from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.collection_transaction import CollectionTransactionCreate, CollectionTransactionOut
from app.schemas.payment import PaymentCreate, PaymentOut
from app.services import collection_transaction_service, payment_service
from app.services.collection_transaction_service import to_out

router = APIRouter(prefix="/collection-transactions", tags=["collection-transactions"])


@router.post("", response_model=CollectionTransactionOut, status_code=201)
def record_collection(
    data: CollectionTransactionCreate,
    db: Session = Depends(get_db),
    staff: User = Depends(require_role(UserRole.COLLECTION_POINT_STAFF)),
) -> CollectionTransactionOut:
    """§06: only Collection-Point Staff record transactions, always at their
    own branch — never a point the client supplies."""
    return collection_transaction_service.record_collection(db, data, staff)


@router.get("", response_model=list[CollectionTransactionOut])
def list_transactions(
    collection_point_id: int | None = None,
    on_date: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CollectionTransactionOut]:
    """§06: Admin sees all branches; Staff is scoped to their own. `on_date`
    powers Phase 9's "today's collections" admin view."""
    if user.role == UserRole.ADMIN:
        return collection_transaction_service.list_transactions(
            db, collection_point_id=collection_point_id, requester=user, on_date=on_date
        )

    if collection_point_id is not None and collection_point_id != user.collection_point_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own collection point")

    return collection_transaction_service.list_transactions(
        db, collection_point_id=user.collection_point_id, requester=user, on_date=on_date
    )


@router.get("/{transaction_id}", response_model=CollectionTransactionOut)
def get_transaction(
    transaction_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> CollectionTransactionOut:
    transaction = collection_transaction_service.get_transaction(db, transaction_id)
    if user.role != UserRole.ADMIN and transaction.collection_point_id != user.collection_point_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own collection point")

    return to_out(transaction, float(transaction.material_rate.rate))


# ---- Payments (Phase 7, blueprint SS25 item 2: manual recording only) ----


@router.post("/{transaction_id}/payments", response_model=PaymentOut, status_code=201)
def record_payment(
    transaction_id: int,
    data: PaymentCreate,
    db: Session = Depends(get_db),
    staff: User = Depends(require_role(UserRole.COLLECTION_POINT_STAFF)),
) -> PaymentOut:
    """§06: staff pay the collector on the spot, at their own branch — same
    scoping as recording the collection itself."""
    return payment_service.record_payment(db, transaction_id, data, staff)


@router.get("/{transaction_id}/payments", response_model=list[PaymentOut])
def list_payments(
    transaction_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[PaymentOut]:
    return payment_service.list_payments(db, transaction_id, user)
