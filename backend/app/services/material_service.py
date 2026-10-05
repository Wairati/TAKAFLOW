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

    material = Material(name=data.name, unit=data.unit, selling_rate=data.selling_rate)
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
# Rates are keyed by (point, material, grade) - `grade=None` is a material's
# ungraded/plain tier. A material can carry any mix of one ungraded tier and
# any number of named graded tiers at once (see MaterialRate's docstring).


def get_current_rate(db: Session, point_id: int, material_id: int, grade: str | None = None) -> MaterialRate | None:
    return db.scalar(
        select(MaterialRate).where(
            MaterialRate.collection_point_id == point_id,
            MaterialRate.material_id == material_id,
            MaterialRate.grade == grade if grade is not None else MaterialRate.grade.is_(None),
            MaterialRate.effective_to.is_(None),
        )
    )


def list_current_rates(db: Session, point_id: int, material_id: int) -> list[MaterialRate]:
    stmt = (
        select(MaterialRate)
        .where(
            MaterialRate.collection_point_id == point_id,
            MaterialRate.material_id == material_id,
            MaterialRate.effective_to.is_(None),
        )
        .order_by(MaterialRate.grade.is_(None).desc(), MaterialRate.grade)
    )
    return list(db.scalars(stmt))


def _rotate_rate(db: Session, point_id: int, material_id: int, new_rate: float, grade: str | None) -> MaterialRate:
    """Close whatever rate is currently open for this (point, material, grade)
    tier, then insert the new one. The two steps are flushed separately so the
    DB never sees two open rows for the same tier at once — which the partial
    unique indexes in SS08 would reject anyway, but this keeps the ordering
    explicit rather than accidental."""
    now = datetime.now(timezone.utc)

    current = get_current_rate(db, point_id, material_id, grade)
    if current is not None:
        current.effective_to = now
        db.flush()

    new_row = MaterialRate(
        material_id=material_id,
        collection_point_id=point_id,
        grade=grade,
        rate=new_rate,
        effective_from=now,
        effective_to=None,
    )
    db.add(new_row)
    db.flush()
    return new_row


def accept_material(
    db: Session, point_id: int, material_id: int, rate: float, admin: User, grade: str | None = None
) -> AcceptedMaterialOut:
    point = db.get(CollectionPoint, point_id)
    if point is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection point not found")
    material = get_material(db, material_id)

    existing_link = db.scalar(
        select(CollectionPointMaterial).where(
            CollectionPointMaterial.collection_point_id == point_id,
            CollectionPointMaterial.material_id == material_id,
        )
    )
    if existing_link is None:
        db.add(CollectionPointMaterial(collection_point_id=point_id, material_id=material_id))

    existing_tier = get_current_rate(db, point_id, material_id, grade)
    if existing_tier is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This material already has a current rate for that grade — use change_rate to update it",
        )

    new_rate = _rotate_rate(db, point_id, material_id, rate, grade)

    audit_service.record(
        db,
        user_id=admin.id,
        action="material.accepted_at_point" if existing_link is None else "material.rate_added",
        entity_type="collection_point_material",
        entity_id=point_id,
        details={"material_id": material_id, "rate": rate, "grade": grade},
    )
    db.commit()
    db.refresh(new_rate)
    return AcceptedMaterialOut.model_validate(
        {"material": material, "rates": list_current_rates(db, point_id, material_id)}
    )


def change_rate(
    db: Session, point_id: int, material_id: int, rate: float, admin: User, grade: str | None = None
) -> MaterialRate:
    if get_current_rate(db, point_id, material_id, grade) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This material/grade is not currently accepted at this collection point",
        )

    new_rate = _rotate_rate(db, point_id, material_id, rate, grade)
    audit_service.record(
        db,
        user_id=admin.id,
        action="material.rate_changed",
        entity_type="collection_point_material",
        entity_id=point_id,
        details={"material_id": material_id, "rate": rate, "grade": grade},
    )
    db.commit()
    db.refresh(new_rate)
    return new_rate


def stop_accepting(db: Session, point_id: int, material_id: int, admin: User) -> None:
    """Retires every current tier (ungraded and graded alike) for this
    material at this branch — the material stops being offered there at all."""
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

    now = datetime.now(timezone.utc)
    for current in list_current_rates(db, point_id, material_id):
        current.effective_to = now

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
        rates = list_current_rates(db, point_id, link.material_id)
        if rates:
            result.append(AcceptedMaterialOut.model_validate({"material": material, "rates": rates}))
    return result


def rate_history(db: Session, point_id: int, material_id: int) -> list[MaterialRate]:
    stmt = (
        select(MaterialRate)
        .where(MaterialRate.collection_point_id == point_id, MaterialRate.material_id == material_id)
        .order_by(MaterialRate.effective_from.desc())
    )
    return list(db.scalars(stmt))
