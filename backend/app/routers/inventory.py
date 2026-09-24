from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.inventory import InventorySaleCreate, InventorySaleOut, InventorySummaryOut
from app.services import inventory_service

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/summary", response_model=list[InventorySummaryOut])
def list_summary(
    collection_point_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[InventorySummaryOut]:
    """§06: Admin sees all branches (optionally filtered); Staff is always
    scoped to their own — the same pattern as collection-transactions."""
    if user.role == UserRole.ADMIN:
        return inventory_service.list_summaries(db, collection_point_id=collection_point_id)

    if collection_point_id is not None and collection_point_id != user.collection_point_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own collection point")

    return inventory_service.list_summaries(db, collection_point_id=user.collection_point_id)


@router.post("/sales", response_model=InventorySaleOut, status_code=201)
def create_sale(
    data: InventorySaleCreate,
    db: Session = Depends(get_db),
    staff: User = Depends(require_role(UserRole.COLLECTION_POINT_STAFF)),
) -> InventorySaleOut:
    """§06: only staff record a sale, always at their own branch — same
    scoping as recording a collection or a payment."""
    return inventory_service.record_sale(db, staff.collection_point_id, data, staff.id)


@router.get("/sales", response_model=list[InventorySaleOut])
def list_sales(
    collection_point_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[InventorySaleOut]:
    if user.role == UserRole.ADMIN:
        if collection_point_id is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="collection_point_id is required")
        return inventory_service.list_sales(db, collection_point_id)

    if collection_point_id is not None and collection_point_id != user.collection_point_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own collection point")

    return inventory_service.list_sales(db, user.collection_point_id)
