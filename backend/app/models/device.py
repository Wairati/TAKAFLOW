from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Device(TimestampMixin, Base):
    """Identifies which physical device/session created offline records (§08).
    Not used until Phase 8 (offline-first collection app) wires up sync."""

    __tablename__ = "device"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "Branch A - Tablet 1"
    collection_point_id: Mapped[int | None] = mapped_column(
        ForeignKey("collection_point.id"), nullable=True
    )
