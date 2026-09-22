from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.material import MaterialCreate, MaterialOut, MaterialUpdate
from app.services import material_service

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("", response_model=list[MaterialOut])
def list_materials(
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[MaterialOut]:
    return material_service.list_materials(db, is_active=is_active)


@router.post("", response_model=MaterialOut, status_code=201)
def create_material(
    data: MaterialCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> MaterialOut:
    return material_service.create_material(db, data, admin)


@router.get("/{material_id}", response_model=MaterialOut)
def get_material(
    material_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
) -> MaterialOut:
    return material_service.get_material(db, material_id)


@router.patch("/{material_id}", response_model=MaterialOut)
def update_material(
    material_id: int,
    data: MaterialUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> MaterialOut:
    return material_service.update_material(db, material_id, data, admin)
