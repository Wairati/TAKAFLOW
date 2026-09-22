from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.collection_transaction import CollectionTransactionCreate, CollectionTransactionOut
from app.services import collection_transaction_service
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
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CollectionTransactionOut]:
    """§06: Admin sees all branches; Staff is scoped to their own."""
    if user.role == UserRole.ADMIN:
        return collection_transaction_service.list_transactions(
            db, collection_point_id=collection_point_id, requester=user
        )

    if collection_point_id is not None and collection_point_id != user.collection_point_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own collection point")

    return collection_transaction_service.list_transactions(
        db, collection_point_id=user.collection_point_id, requester=user
    )


@router.get("/{transaction_id}", response_model=CollectionTransactionOut)
def get_transaction(
    transaction_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> CollectionTransactionOut:
    transaction = collection_transaction_service.get_transaction(db, transaction_id)
    if user.role != UserRole.ADMIN and transaction.collection_point_id != user.collection_point_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own collection point")

    return to_out(transaction, float(transaction.material_rate.rate))
