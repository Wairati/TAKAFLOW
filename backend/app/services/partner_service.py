from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.partner import Partner
from app.models.user import User
from app.schemas.partner import PartnerCreate, PartnerUpdate
from app.services import audit_service


def list_partners(db: Session, *, is_active: bool | None = None) -> list[Partner]:
    stmt = select(Partner)
    if is_active is not None:
        stmt = stmt.where(Partner.is_active == is_active)
    return list(db.scalars(stmt.order_by(Partner.name)))


def get_partner(db: Session, partner_id: int) -> Partner:
    partner = db.get(Partner, partner_id)
    if partner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
    return partner


def create_partner(db: Session, data: PartnerCreate, admin: User) -> Partner:
    if db.scalar(select(Partner).where(Partner.name == data.name)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A partner with this name already exists")

    partner = Partner(name=data.name, contact_person=data.contact_person, phone=data.phone)
    db.add(partner)
    db.flush()
    audit_service.record(
        db,
        user_id=admin.id,
        action="partner.created",
        entity_type="partner",
        entity_id=partner.id,
        details={"name": partner.name},
    )
    db.commit()
    db.refresh(partner)
    return partner


def update_partner(db: Session, partner_id: int, data: PartnerUpdate, admin: User) -> Partner:
    partner = get_partner(db, partner_id)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(partner, field, value)

    if changes:
        audit_service.record(
            db,
            user_id=admin.id,
            action="partner.updated",
            entity_type="partner",
            entity_id=partner.id,
            details=changes,
        )
    db.commit()
    db.refresh(partner)
    return partner
