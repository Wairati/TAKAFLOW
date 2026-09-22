import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class MovementType(str, enum.Enum):
    """§11. Only COLLECTION and ADJUSTMENT are actually produced by this build's
    code (matching/transfers are deferred, §22) — the rest of the enum exists
    now so the ledger's shape doesn't need a migration when that work resumes."""

    COLLECTION = "collection"
    TRANSFER_OUT = "transfer_out"
    RESERVATION = "reservation"
    RESERVATION_RELEASE = "reservation_release"
    ADJUSTMENT = "adjustment"


class InventoryLedger(TimestampMixin, Base):
    """Append-only. Never updated, never deleted — a correction is a new,
    reversing row, not an edit (§11). This table, not inventory_summary, is
    the source of truth; the summary is a derived read cache of it."""

    __tablename__ = "inventory_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_point_id: Mapped[int] = mapped_column(
        ForeignKey("collection_point.id"), nullable=False
    )
    material_id: Mapped[int] = mapped_column(ForeignKey("material.id"), nullable=False)
    movement_type: Mapped[MovementType] = mapped_column(
        Enum(MovementType, name="movement_type"), nullable=False
    )
    quantity_delta: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # Polymorphic pointer to whatever caused this movement (a collection_transaction
    # today; a transfer/reservation once that work resumes) — plain string rather
    # than a DB enum so a new reference type never needs a migration of its own.
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[int] = mapped_column(nullable=False)


class InventorySummary(Base):
    """Derived, fast-read balance per (collection_point, material). Every write
    here happens in the same DB transaction as the ledger insert that caused it,
    via an atomic `quantity_on_hand = quantity_on_hand + :delta` — never a
    read-then-write in application code (§11)."""

    __tablename__ = "inventory_summary"
    __table_args__ = (
        CheckConstraint("quantity_on_hand >= 0", name="ck_on_hand_non_negative"),
        CheckConstraint("quantity_reserved >= 0", name="ck_reserved_non_negative"),
    )

    collection_point_id: Mapped[int] = mapped_column(
        ForeignKey("collection_point.id"), primary_key=True
    )
    material_id: Mapped[int] = mapped_column(ForeignKey("material.id"), primary_key=True)

    quantity_on_hand: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    quantity_reserved: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
