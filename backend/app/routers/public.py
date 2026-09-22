"""Phase 12: the public website's data source. §05: no authentication, only
active branches, and only what's meant to be advertised — a branch's
accepted materials and current rates are exactly what a walk-in collector
needs to decide where to bring material."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.collection_point import CollectionPointOut
from app.schemas.material import AcceptedMaterialOut
from app.services import collection_point_service, material_service

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/collection-points", response_model=list[CollectionPointOut])
def list_active_collection_points(db: Session = Depends(get_db)) -> list[CollectionPointOut]:
    return collection_point_service.list_points(db, is_active=True)


@router.get("/collection-points/{point_id}/materials", response_model=list[AcceptedMaterialOut])
def list_active_point_materials(point_id: int, db: Session = Depends(get_db)) -> list[AcceptedMaterialOut]:
    point = collection_point_service.get_point(db, point_id)
    if not point.is_active:
        # Same 404 as "doesn't exist" - a deactivated branch's details aren't
        # public information either.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection point not found")
    return material_service.list_accepted_materials(db, point_id)
