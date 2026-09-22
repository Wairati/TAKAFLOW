from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.collection_point import CollectionPoint
from app.models.user import User
from app.schemas.collection_point import CollectionPointCreate, CollectionPointUpdate
from app.services import audit_service


def list_points(db: Session, *, is_active: bool | None = None) -> list[CollectionPoint]:
    stmt = select(CollectionPoint)
    if is_active is not None:
        stmt = stmt.where(CollectionPoint.is_active == is_active)
    return list(db.scalars(stmt.order_by(CollectionPoint.name)))


def get_point(db: Session, point_id: int) -> CollectionPoint:
    point = db.get(CollectionPoint, point_id)
    if point is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection point not found")
    return point


def create_point(db: Session, data: CollectionPointCreate, admin: User) -> CollectionPoint:
    point = CollectionPoint(**data.model_dump())
    db.add(point)
    db.flush()  # assigns point.id without ending the transaction
    audit_service.record(
        db,
        user_id=admin.id,
        action="collection_point.created",
        entity_type="collection_point",
        entity_id=point.id,
        details={"name": point.name},
    )
    db.commit()
    db.refresh(point)
    return point


def update_point(db: Session, point_id: int, data: CollectionPointUpdate, admin: User) -> CollectionPoint:
    point = get_point(db, point_id)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(point, field, value)

    if changes:
        audit_service.record(
            db,
            user_id=admin.id,
            action="collection_point.updated",
            entity_type="collection_point",
            entity_id=point.id,
            details=changes,
        )
    db.commit()
    db.refresh(point)
    return point
