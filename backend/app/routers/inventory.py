from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.inventory import InventorySummaryOut
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
