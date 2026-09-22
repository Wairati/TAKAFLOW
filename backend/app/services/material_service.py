from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.collection_point import CollectionPoint
from app.models.material import CollectionPointMaterial, Material, MaterialRate
from app.models.user import User
from app.schemas.material import AcceptedMaterialOut, MaterialCreate, MaterialUpdate
from app.services import audit_service


# ---- Materials -----------------------------------------------------------


def list_materials(db: Session, *, is_active: bool | None = None) -> list[Material]:
    stmt = select(Material)
    if is_active is not None:
        stmt = stmt.where(Material.is_active == is_active)
    return list(db.scalars(stmt.order_by(Material.name)))


def get_material(db: Session, material_id: int) -> Material:
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    return material


def create_material(db: Session, data: MaterialCreate, admin: User) -> Material:
    if db.scalar(select(Material).where(Material.name == data.name)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A material with this name already exists")

    material = Material(name=data.name, unit=data.unit)
    db.add(material)
    db.flush()
    audit_service.record(
        db,
        user_id=admin.id,
        action="material.created",
        entity_type="material",
        entity_id=material.id,
        details={"name": material.name, "unit": material.unit},
    )
    db.commit()
    db.refresh(material)
    return material


def update_material(db: Session, material_id: int, data: MaterialUpdate, admin: User) -> Material:
    material = get_material(db, material_id)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(material, field, value)

    if changes:
        audit_service.record(
            db,
            user_id=admin.id,
            action="material.updated",
            entity_type="material",
            entity_id=material.id,
            details=changes,
        )
    db.commit()
    db.refresh(material)
    return material


# ---- Per-point acceptance & rate history (blueprint SS08 challenges 2 & 3) ----


def get_current_rate(db: Session, point_id: int, material_id: int) -> MaterialRate | None:
    return db.scalar(
        select(MaterialRate).where(
            MaterialRate.collection_point_id == point_id,
            MaterialRate.material_id == material_id,
            MaterialRate.effective_to.is_(None),
        )
    )


def _rotate_rate(db: Session, point_id: int, material_id: int, new_rate: float) -> MaterialRate:
    """Close whatever rate is currently open, then insert the new one. The two
    steps are flushed separately so the DB never sees two open rows for the
    same (material, point) at once — which the partial unique index in SS08
    would reject anyway, but this keeps the ordering explicit rather than
    accidental."""
    now = datetime.now(timezone.utc)

    current = get_current_rate(db, point_id, material_id)
    if current is not None:
        current.effective_to = now
        db.flush()

    new_row = MaterialRate(
        material_id=material_id,
        collection_point_id=point_id,
        rate=new_rate,
        effective_from=now,
        effective_to=None,
    )
    db.add(new_row)
    db.flush()
    return new_row


def accept_material(db: Session, point_id: int, material_id: int, rate: float, admin: User) -> AcceptedMaterialOut:
    point = db.get(CollectionPoint, point_id)
    if point is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection point not found")
    material = get_material(db, material_id)

    existing = db.scalar(
        select(CollectionPointMaterial).where(
            CollectionPointMaterial.collection_point_id == point_id,
            CollectionPointMaterial.material_id == material_id,
        )
    )
    if existing is None:
        db.add(CollectionPointMaterial(collection_point_id=point_id, material_id=material_id))

    new_rate = _rotate_rate(db, point_id, material_id, rate)

    audit_service.record(
        db,
        user_id=admin.id,
        action="material.accepted_at_point" if existing is None else "material.rate_changed",
        entity_type="collection_point_material",
        entity_id=point_id,
        details={"material_id": material_id, "rate": rate},
    )
    db.commit()
    db.refresh(new_rate)
    return AcceptedMaterialOut.model_validate({"material": material, "current_rate": new_rate})


def change_rate(db: Session, point_id: int, material_id: int, rate: float, admin: User) -> MaterialRate:
    if get_current_rate(db, point_id, material_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This material is not currently accepted at this collection point",
        )

    new_rate = _rotate_rate(db, point_id, material_id, rate)
    audit_service.record(
        db,
        user_id=admin.id,
        action="material.rate_changed",
        entity_type="collection_point_material",
        entity_id=point_id,
        details={"material_id": material_id, "rate": rate},
    )
    db.commit()
    db.refresh(new_rate)
    return new_rate


def stop_accepting(db: Session, point_id: int, material_id: int, admin: User) -> None:
    link = db.scalar(
        select(CollectionPointMaterial).where(
            CollectionPointMaterial.collection_point_id == point_id,
            CollectionPointMaterial.material_id == material_id,
        )
    )
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This material is not currently accepted at this collection point",
        )

    current = get_current_rate(db, point_id, material_id)
    if current is not None:
        current.effective_to = datetime.now(timezone.utc)

    db.delete(link)
    audit_service.record(
        db,
        user_id=admin.id,
        action="material.stopped_accepting",
        entity_type="collection_point_material",
        entity_id=point_id,
        details={"material_id": material_id},
    )
    db.commit()


def list_accepted_materials(db: Session, point_id: int) -> list[AcceptedMaterialOut]:
    links = db.scalars(
        select(CollectionPointMaterial).where(CollectionPointMaterial.collection_point_id == point_id)
    )
    result = []
    for link in links:
        material = get_material(db, link.material_id)
        current_rate = get_current_rate(db, point_id, link.material_id)
        if current_rate is not None:
            result.append(AcceptedMaterialOut.model_validate({"material": material, "current_rate": current_rate}))
    return result


def rate_history(db: Session, point_id: int, material_id: int) -> list[MaterialRate]:
    stmt = (
        select(MaterialRate)
        .where(MaterialRate.collection_point_id == point_id, MaterialRate.material_id == material_id)
        .order_by(MaterialRate.effective_from.desc())
    )
    return list(db.scalars(stmt))
