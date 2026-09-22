import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class CollectionTransaction(TimestampMixin, Base):
    """An immutable record of one delivery. §25 item 7: the collector is a
    walk-in — no supplier entity, no registration, just optional details kept
    for the payment/dispute record. §25 item 4: grade is captured inline."""

    __tablename__ = "collection_transaction"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The offline-sync idempotency key (§10): the client generates this once,
    # and this UNIQUE constraint is what makes a duplicate submit a no-op
    # instead of a double-counted collection.
    client_transaction_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False
    )

    collection_point_id: Mapped[int] = mapped_column(
        ForeignKey("collection_point.id"), nullable=False
    )
    material_id: Mapped[int] = mapped_column(ForeignKey("material.id"), nullable=False)
    material_rate_id: Mapped[int] = mapped_column(
        ForeignKey("material_rate.id"), nullable=False
    )
    recorded_by_user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)

    # Which physical device/session this came from — relevant once offline
    # sync (Phase 8) is wired up; NULL for anything recorded online today.
    device_id: Mapped[int | None] = mapped_column(ForeignKey("device.id"), nullable=True)

    quantity: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    grade: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Walk-in collector details — optional, never deduplicated (§25 item 7).
    collector_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    collector_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # When the collection actually happened, as reported by the client — kept
    # separate from created_at (when the server received/synced it), because
    # §11 posts to the inventory ledger using sync time, not this timestamp.
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
