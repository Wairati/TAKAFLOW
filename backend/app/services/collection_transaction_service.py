"""Phase 6: recording a walk-in collection (SS25 item 7 — no supplier entity,
no registration) and posting it to the Phase 5 inventory ledger. Online-only
for now; Phase 8 adds the offline outbox on top without changing this."""

from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.collection_transaction import CollectionTransaction
from app.models.inventory import MovementType
from app.models.user import User
from app.schemas.collection_transaction import CollectionTransactionCreate, CollectionTransactionOut
from app.services import inventory_service, material_service


def to_out(transaction: CollectionTransaction, rate: float) -> CollectionTransactionOut:
    return CollectionTransactionOut(
        id=transaction.id,
        client_transaction_uuid=transaction.client_transaction_uuid,
        collection_point_id=transaction.collection_point_id,
        material_id=transaction.material_id,
        material_rate_id=transaction.material_rate_id,
        rate=rate,
        recorded_by_user_id=transaction.recorded_by_user_id,
        quantity=transaction.quantity,
        grade=transaction.grade,
        collector_name=transaction.collector_name,
        collector_phone=transaction.collector_phone,
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
        return to_out(existing, float(existing.material_rate.rate))

    current_rate = material_service.get_current_rate(db, staff.collection_point_id, data.material_id)
    if current_rate is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This material is not currently accepted at your collection point",
        )

    transaction = CollectionTransaction(
        client_transaction_uuid=data.client_transaction_uuid,
        collection_point_id=staff.collection_point_id,
        material_id=data.material_id,
        material_rate_id=current_rate.id,
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
    return to_out(transaction, float(current_rate.rate))


def list_transactions(
    db: Session, *, collection_point_id: int | None, requester: User, on_date: date | None = None
) -> list[CollectionTransactionOut]:
    stmt = select(CollectionTransaction).order_by(CollectionTransaction.occurred_at.desc())
    if collection_point_id is not None:
        stmt = stmt.where(CollectionTransaction.collection_point_id == collection_point_id)
    if on_date is not None:
        # Phase 9: the admin "today's collections" view - filters on the
        # client-reported occurred_at, not created_at/sync time.
        stmt = stmt.where(func.date(CollectionTransaction.occurred_at) == on_date)

    rows = db.scalars(stmt).all()
    return [to_out(row, float(row.material_rate.rate)) for row in rows]


def get_transaction(db: Session, transaction_id: int) -> CollectionTransaction:
    transaction = db.get(CollectionTransaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection transaction not found")
    return transaction
