"""Phase 7: manual payment recording (SS25 item 2 — method + reference, no
live M-Pesa/Daraja disbursement). A transaction may have more than one
payment (blueprint SS08: the FK is one-to-many), so this never enforces
"already paid" — it just records what staff say happened."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.collection_transaction import CollectionTransaction
from app.models.payment import Payment, PaymentMethod
from app.models.user import User, UserRole
from app.schemas.payment import PaymentCreate


def _get_transaction_scoped(db: Session, transaction_id: int, requester: User) -> CollectionTransaction:
    transaction = db.get(CollectionTransaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection transaction not found")
    if requester.role != UserRole.ADMIN and transaction.collection_point_id != requester.collection_point_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You can only access your own collection point"
        )
    return transaction


def record_payment(db: Session, transaction_id: int, data: PaymentCreate, staff: User) -> Payment:
    transaction = _get_transaction_scoped(db, transaction_id, staff)

    if transaction.partner_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This was a collaborative collection — no payment is expected for it",
        )
    if data.amount <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Amount must be positive")
    if data.method == PaymentMethod.MPESA and not data.reference_number:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="An M-Pesa payment must include a reference (the confirmation code)",
        )

    payment = Payment(
        collection_transaction_id=transaction.id,
        method=data.method,
        amount=data.amount,
        reference_number=data.reference_number,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def list_payments(db: Session, transaction_id: int, requester: User) -> list[Payment]:
    _get_transaction_scoped(db, transaction_id, requester)
    stmt = select(Payment).where(Payment.collection_transaction_id == transaction_id).order_by(Payment.created_at)
    return list(db.scalars(stmt))
