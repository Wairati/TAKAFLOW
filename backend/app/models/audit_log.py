from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AuditLog(TimestampMixin, Base):
    """Admin/config change trail (§18) — who changed what, distinct from the
    operational sync_log. Not written to until admin CRUD exists (Phase 4)."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "material.rate_changed"
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[int] = mapped_column(nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
