"""Phase 6: recording a walk-in collection (SS25 item 7 — no supplier entity,
no registration) and posting it to the Phase 5 inventory ledger. Online-only
for now; Phase 8 adds the offline outbox on top without changing this."""

from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.collection_point import CollectionPoint
from app.models.collection_transaction import CollectionTransaction
from app.models.inventory import MovementType
from app.models.material import Material
from app.models.partner import Partner
from app.models.user import User
from app.schemas.collection_transaction import CollectionTransactionCreate, CollectionTransactionOut
from app.services import inventory_service, material_service


def to_out(transaction: CollectionTransaction) -> CollectionTransactionOut:
    return CollectionTransactionOut(
        id=transaction.id,
        client_transaction_uuid=transaction.client_transaction_uuid,
        collection_point_id=transaction.collection_point_id,
        material_id=transaction.material_id,
        material_rate_id=transaction.material_rate_id,
        rate=float(transaction.material_rate.rate) if transaction.material_rate else None,
        recorded_by_user_id=transaction.recorded_by_user_id,
        quantity=transaction.quantity,
        grade=transaction.grade,
        collector_name=transaction.collector_name,
        collector_phone=transaction.collector_phone,
        partner_id=transaction.partner_id,
        occurred_at=transaction.occurred_at,
        created_at=transaction.created_at,
    )


def record_collection(
    db: Session, data: CollectionTransactionCreate, staff: User
) -> CollectionTransactionOut:
    if staff.collection_point_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your account has no assigned collection point — ask an admin to set one",
        )
    if data.quantity <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Quantity must be positive")

    # Idempotency (SS10): a duplicate client_transaction_uuid is answered with
    # the original record, as a success, not an error — this is what makes a
    # double-tap or a retried submit safe to replay.
    existing = db.scalar(
        select(CollectionTransaction).where(
            CollectionTransaction.client_transaction_uuid == data.client_transaction_uuid
        )
    )
    if existing is not None:
        # Idempotent replay always succeeds regardless of what's changed
        # since the original was recorded (SS10) - the checks below apply
        # only to genuinely new transactions.
        return to_out(existing)

    # Phase 14 hardening: deactivating a branch or a material (Phase 4)
    # didn't used to stop new collections against it (Phase 6) - closing a
    # material_rate row isn't the same as the material/point being active,
    # and get_current_rate only ever checked the former.
    point = db.get(CollectionPoint, staff.collection_point_id)
    if point is None or not point.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Your collection point is no longer active"
        )
    material = db.get(Material, data.material_id)
    if material is None or not material.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This material is no longer active"
        )

    # A collaborative collection (contributed by a partner organisation, e.g.
    # an environmental conservation group) skips the rate lookup entirely —
    # no payment is ever expected for it, so there's nothing to price.
    if data.partner_id is not None:
        partner = db.get(Partner, data.partner_id)
        if partner is None or not partner.is_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This partner is not currently active")
        current_rate = None
    else:
        current_rate = material_service.get_current_rate(db, staff.collection_point_id, data.material_id, data.grade)
        if current_rate is None:
            any_rates = material_service.list_current_rates(db, staff.collection_point_id, data.material_id)
            if not any_rates:
                detail = "This material is not currently accepted at your collection point"
            elif data.grade is None:
                detail = "Select a grade for this material"
            else:
                detail = f'"{data.grade}" is not a configured grade for this material — check the grade options'
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    transaction = CollectionTransaction(
        client_transaction_uuid=data.client_transaction_uuid,
        collection_point_id=staff.collection_point_id,
        material_id=data.material_id,
        material_rate_id=current_rate.id if current_rate else None,
        partner_id=data.partner_id,
        recorded_by_user_id=staff.id,
        device_id=None,  # Phase 8: set once offline devices are identified
        quantity=data.quantity,
        grade=data.grade,
        collector_name=data.collector_name,
        collector_phone=data.collector_phone,
        occurred_at=data.occurred_at or datetime.now(timezone.utc),
    )
    db.add(transaction)
    db.flush()  # assigns transaction.id, inside this same still-open transaction

    # SS11: exactly one ledger entry per transaction, in the same transaction
    # as the transaction row itself — both succeed or both roll back together.
    # Material still physically arrives regardless of whether it was paid
    # for, so a collaborative collection posts to inventory the same way.
    inventory_service.post_movement(
        db,
        collection_point_id=staff.collection_point_id,
        material_id=data.material_id,
        movement_type=MovementType.COLLECTION,
        quantity=data.quantity,
        reference_type="collection_transaction",
        reference_id=transaction.id,
    )

    db.commit()
    db.refresh(transaction)
    return to_out(transaction)


def list_transactions(
    db: Session, *, collection_point_id: int | None, requester: User, on_date: date | None = None
) -> list[CollectionTransactionOut]:
    stmt = select(CollectionTransaction).order_by(CollectionTransaction.occurred_at.desc())
    if collection_point_id is not None:
        stmt = stmt.where(CollectionTransaction.collection_point_id == collection_point_id)
    if on_date is not None:
        # Phase 9: the admin "today's collections" view - filters on the
        # client-reported occurred_at, not created_at/sync time.
        #
        # Phase 14 hardening: func.date() alone buckets by the DATABASE
        # SESSION's default timezone, not a fixed one - on this dev machine
        # that happens to already be Africa/Nairobi (inherited from the OS),
        # which made this look correct without actually being guaranteed to
        # be. A managed Postgres host (Neon/Supabase, SS20's deployment
        # target) defaults to UTC, which would misattribute any collection
        # made between midnight and 3am EAT to the previous calendar day.
        # The business operates in one timezone, so converting explicitly
        # is simpler and correct than making this configurable per branch.
        local_date = func.date(func.timezone("Africa/Nairobi", CollectionTransaction.occurred_at))
        stmt = stmt.where(local_date == on_date)

    rows = db.scalars(stmt).all()
    return [to_out(row) for row in rows]


def get_transaction(db: Session, transaction_id: int) -> CollectionTransaction:
    transaction = db.get(CollectionTransaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection transaction not found")
    return transaction
