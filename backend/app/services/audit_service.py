from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record(
    db: Session, *, user_id: int, action: str, entity_type: str, entity_id: int, details: dict | None = None
) -> None:
    """§18: the admin/config accountability trail. Callers commit alongside
    their own change — this does not commit on its own, so an audit entry
    never gets written for a change that itself failed to save."""
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
    )
