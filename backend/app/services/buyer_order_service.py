"""Buyer orders: an external buyer's standing request for a quantity of one
material, fulfilled from one branch's stock. Any member of staff or an admin
can take an order and record the buyer's payment against it; recording a
payment is itself the approval (no separate verification step) and, in the
same step, decrements that branch's inventory — physically handing the
material over happens outside the system.

Lifecycle: OPEN -> (a payment is recorded, by staff or an admin) -> PAID.
CANCELLED is reachable from OPEN only."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.buyer_order import BuyerOrder, BuyerOrderPayment, BuyerOrderStatus
from app.models.collection_point import CollectionPoint
from app.models.inventory import MovementType
from app.models.material import Material
from app.models.payment import PaymentMethod
from app.models.user import User, UserRole
from app.schemas.buyer_order import BuyerOrderCreate, BuyerOrderOut, BuyerOrderPaymentCreate
from app.services import audit_service, inventory_service


def _get_order(db: Session, order_id: int) -> BuyerOrder:
    order = db.get(BuyerOrder, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyer order not found")
    return order


def to_out(db: Session, order: BuyerOrder) -> BuyerOrderOut:
    material = db.get(Material, order.material_id)
    point = db.get(CollectionPoint, order.collection_point_id)
    return BuyerOrderOut(
        id=order.id,
        collection_point_id=order.collection_point_id,
        collection_point_name=point.name if point else "",
        buyer_name=order.buyer_name,
        buyer_phone=order.buyer_phone,
        material_id=order.material_id,
        material_name=material.name if material else "",
        unit=material.unit if material else "",
        quantity_requested=float(order.quantity_requested),
        status=order.status,
        notes=order.notes,
        created_by_user_id=order.created_by_user_id,
        created_at=order.created_at,
    )


def _resolve_collection_point_id(data: BuyerOrderCreate, creator: User) -> int:
    """Staff always order against their own branch; an admin has no branch of
    their own, so they must say which one this order is for."""
    if creator.role == UserRole.ADMIN:
        if data.collection_point_id is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Select a branch for this order")
        return data.collection_point_id

    if creator.collection_point_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your account has no assigned collection point — ask an admin to set one",
        )
    return creator.collection_point_id


def create_order(db: Session, data: BuyerOrderCreate, creator: User) -> BuyerOrderOut:
    if data.quantity_requested <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Quantity requested must be positive")
    material = db.get(Material, data.material_id)
    if material is None or not material.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This material is no longer active")
    if not data.buyer_name.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Please enter the buyer's name")

    collection_point_id = _resolve_collection_point_id(data, creator)
    point = db.get(CollectionPoint, collection_point_id)
    if point is None or not point.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That branch is no longer active")

    order = BuyerOrder(
        collection_point_id=collection_point_id,
        buyer_name=data.buyer_name.strip(),
        buyer_phone=data.buyer_phone,
        material_id=data.material_id,
        quantity_requested=data.quantity_requested,
        notes=data.notes,
        created_by_user_id=creator.id,
    )
    db.add(order)
    db.flush()
    audit_service.record(
        db,
        user_id=creator.id,
        action="buyer_order.created",
        entity_type="buyer_order",
        entity_id=order.id,
        details={"buyer_name": order.buyer_name, "material_id": order.material_id, "quantity_requested": data.quantity_requested},
    )
    db.commit()
    db.refresh(order)
    return to_out(db, order)


def list_orders(db: Session, *, status_filter: BuyerOrderStatus | None) -> list[BuyerOrderOut]:
    stmt = select(BuyerOrder).order_by(BuyerOrder.created_at.desc())
    if status_filter is not None:
        stmt = stmt.where(BuyerOrder.status == status_filter)
    return [to_out(db, order) for order in db.scalars(stmt)]


def get_order(db: Session, order_id: int) -> BuyerOrderOut:
    return to_out(db, _get_order(db, order_id))


def cancel_order(db: Session, order_id: int, admin: User) -> BuyerOrderOut:
    order = _get_order(db, order_id)
    if order.status != BuyerOrderStatus.OPEN:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"This order is already {order.status.value}")

    order.status = BuyerOrderStatus.CANCELLED
    order.cancelled_at = datetime.now(timezone.utc)
    audit_service.record(
        db, user_id=admin.id, action="buyer_order.cancelled", entity_type="buyer_order", entity_id=order.id
    )
    db.commit()
    db.refresh(order)
    return to_out(db, order)


# ---- Payments (money IN from the buyer) -----------------------------------


def record_payment(db: Session, order_id: int, data: BuyerOrderPaymentCreate, recorder: User) -> BuyerOrderPayment:
    """Recording a payment IS the approval — whoever takes it (staff or
    admin) can confirm it themselves, no separate admin sign-off. This moves
    the order straight to PAID and, in the same step, posts a SALE movement
    against the order's branch for the full requested quantity — the same
    inventory ledger a collection posts to."""
    order = _get_order(db, order_id)
    if order.status != BuyerOrderStatus.OPEN:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"This order is already {order.status.value}")
    if data.method == PaymentMethod.MPESA and not data.reference_number:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="An M-Pesa payment must include a reference (the confirmation code)",
        )

    material = db.get(Material, order.material_id)
    if material is None or material.selling_rate is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This material has no selling rate set — ask an admin to set one before recording payment",
        )
    amount = float(material.selling_rate) * float(order.quantity_requested)

    payment = BuyerOrderPayment(
        buyer_order_id=order.id,
        amount=amount,
        method=data.method,
        reference_number=data.reference_number,
        recorded_by_user_id=recorder.id,
    )
    db.add(payment)
    db.flush()  # assign payment.id for the ledger's reference_id

    try:
        inventory_service.post_movement(
            db,
            collection_point_id=order.collection_point_id,
            material_id=order.material_id,
            movement_type=MovementType.SALE,
            quantity=float(order.quantity_requested),
            reference_type="buyer_order_payment",
            reference_id=payment.id,
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Not enough of that material on hand at that branch to fulfil this order",
        ) from exc

    order.status = BuyerOrderStatus.PAID

    audit_service.record(
        db, user_id=recorder.id, action="buyer_order.paid", entity_type="buyer_order", entity_id=order.id,
        details={"amount": amount},
    )

    db.commit()
    db.refresh(payment)
    return payment


def list_payments(db: Session, order_id: int) -> list[BuyerOrderPayment]:
    _get_order(db, order_id)
    stmt = (
        select(BuyerOrderPayment)
        .where(BuyerOrderPayment.buyer_order_id == order_id)
        .order_by(BuyerOrderPayment.created_at)
    )
    return list(db.scalars(stmt))
