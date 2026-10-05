from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.partner import PartnerCreate, PartnerOut, PartnerUpdate
from app.services import partner_service

router = APIRouter(prefix="/partners", tags=["partners"])


@router.get("", response_model=list[PartnerOut])
def list_partners(
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[PartnerOut]:
    return partner_service.list_partners(db, is_active=is_active)


@router.post("", response_model=PartnerOut, status_code=201)
def create_partner(
    data: PartnerCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> PartnerOut:
    return partner_service.create_partner(db, data, admin)


@router.get("/{partner_id}", response_model=PartnerOut)
def get_partner(
    partner_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
) -> PartnerOut:
    return partner_service.get_partner(db, partner_id)


@router.patch("/{partner_id}", response_model=PartnerOut)
def update_partner(
    partner_id: int,
    data: PartnerUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> PartnerOut:
    return partner_service.update_partner(db, partner_id, data, admin)
