from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.report import ReportsSummaryOut
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary", response_model=ReportsSummaryOut)
def get_summary(
    from_date: date,
    to_date: date,
    collection_point_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ReportsSummaryOut:
    """§06: Admin must specify a branch (there's no meaningful "all branches"
    total to add materials/money across); Staff is always scoped to their own
    — the same pattern as inventory and collection-transactions."""
    if from_date > to_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="from_date must not be after to_date")

    if user.role == UserRole.ADMIN:
        if collection_point_id is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="collection_point_id is required")
        return report_service.get_summary(db, collection_point_id, from_date, to_date)

    if collection_point_id is not None and collection_point_id != user.collection_point_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own collection point")
    if user.collection_point_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your account has no assigned collection point — ask an admin to set one",
        )

    return report_service.get_summary(db, user.collection_point_id, from_date, to_date)
