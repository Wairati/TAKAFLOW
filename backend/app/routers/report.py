from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.report import ReportsByBranchOut, ReportsSummaryOut, ReportsTimeseriesOut
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


def _resolve_scope(user: User, collection_point_id: int | None) -> int | None:
    """§06: Staff is always scoped to their own branch. Admin may specify a
    branch, or omit it to mean "every active branch combined" — the one place
    a company-wide total makes sense to add materials/money across."""
    if user.role == UserRole.ADMIN:
        return collection_point_id

    if collection_point_id is not None and collection_point_id != user.collection_point_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own collection point")
    if user.collection_point_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your account has no assigned collection point — ask an admin to set one",
        )
    return user.collection_point_id


@router.get("/summary", response_model=ReportsSummaryOut)
def get_summary(
    from_date: date,
    to_date: date,
    collection_point_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ReportsSummaryOut:
    if from_date > to_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="from_date must not be after to_date")
    scoped_point_id = _resolve_scope(user, collection_point_id)
    return report_service.get_summary(db, scoped_point_id, from_date, to_date)


@router.get("/timeseries", response_model=ReportsTimeseriesOut)
def get_timeseries(
    from_date: date,
    to_date: date,
    collection_point_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ReportsTimeseriesOut:
    if from_date > to_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="from_date must not be after to_date")
    scoped_point_id = _resolve_scope(user, collection_point_id)
    return report_service.get_timeseries(db, scoped_point_id, from_date, to_date)


@router.get("/by-branch", response_model=ReportsByBranchOut)
def get_by_branch(
    from_date: date,
    to_date: date,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role(UserRole.ADMIN)),
) -> ReportsByBranchOut:
    if from_date > to_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="from_date must not be after to_date")
    return report_service.get_by_branch(db, from_date, to_date)
