import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class SyncStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    CONFLICT = "conflict"


class SyncLog(TimestampMixin, Base):
    """Per-attempt audit trail for offline sync (§10, §18) — operational, distinct
    from audit_log (admin/config accountability). Not used until Phase 8."""

    __tablename__ = "sync_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("device.id"), nullable=False)
    client_transaction_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    status: Mapped[SyncStatus] = mapped_column(Enum(SyncStatus, name="sync_status"), nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
