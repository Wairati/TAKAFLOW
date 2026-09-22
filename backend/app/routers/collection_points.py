from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.material import MaterialRate
from app.models.user import User, UserRole
from app.schemas.collection_point import CollectionPointCreate, CollectionPointOut, CollectionPointUpdate
from app.schemas.material import AcceptedMaterialOut, AcceptMaterialRequest, MaterialRateOut, SetRateRequest
from app.services import collection_point_service, material_service

router = APIRouter(prefix="/collection-points", tags=["collection-points"])


@router.get("", response_model=list[CollectionPointOut])
def list_points(
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[CollectionPointOut]:
    return collection_point_service.list_points(db, is_active=is_active)


@router.post("", response_model=CollectionPointOut, status_code=201)
def create_point(
    data: CollectionPointCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> CollectionPointOut:
    return collection_point_service.create_point(db, data, admin)


@router.get("/{point_id}", response_model=CollectionPointOut)
def get_point(
    point_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
) -> CollectionPointOut:
    return collection_point_service.get_point(db, point_id)


@router.patch("/{point_id}", response_model=CollectionPointOut)
def update_point(
    point_id: int,
    data: CollectionPointUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> CollectionPointOut:
    return collection_point_service.update_point(db, point_id, data, admin)


# ---- Materials accepted at this point, and their rate history ----


@router.get("/{point_id}/materials", response_model=list[AcceptedMaterialOut])
def list_accepted_materials(
    point_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
) -> list[AcceptedMaterialOut]:
    return material_service.list_accepted_materials(db, point_id)


@router.post("/{point_id}/materials", response_model=AcceptedMaterialOut, status_code=201)
def accept_material(
    point_id: int,
    data: AcceptMaterialRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> AcceptedMaterialOut:
    return material_service.accept_material(db, point_id, data.material_id, data.rate, admin)


@router.patch("/{point_id}/materials/{material_id}/rate", response_model=MaterialRateOut)
def change_rate(
    point_id: int,
    material_id: int,
    data: SetRateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> MaterialRate:
    return material_service.change_rate(db, point_id, material_id, data.rate, admin)


@router.delete("/{point_id}/materials/{material_id}", status_code=204)
def stop_accepting(
    point_id: int,
    material_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> None:
    material_service.stop_accepting(db, point_id, material_id, admin)


@router.get("/{point_id}/materials/{material_id}/rate-history", response_model=list[MaterialRateOut])
def rate_history(
    point_id: int, material_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
) -> list[MaterialRate]:
    return material_service.rate_history(db, point_id, material_id)
