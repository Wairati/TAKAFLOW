from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Material(TimestampMixin, Base):
    """§08 challenge 2: no `purchase_rate` field here — see MaterialRate below."""

    __tablename__ = "material"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "kg"
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class CollectionPointMaterial(Base):
    """§08 challenge 3: which materials a branch accepts — the public site's
    eventual source of truth for 'materials accepted at each collection point'."""

    __tablename__ = "collection_point_material"
    __table_args__ = (
        UniqueConstraint("collection_point_id", "material_id", name="uq_point_material"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_point_id: Mapped[int] = mapped_column(
        ForeignKey("collection_point.id"), nullable=False
    )
    material_id: Mapped[int] = mapped_column(ForeignKey("material.id"), nullable=False)


class MaterialRate(TimestampMixin, Base):
    """§08 challenge 2, time- and branch-scoped rate history. Every rate is tied
    to a specific branch (no NULL/'global default' row) — deliberately, so the
    'exactly one current rate' rule below can be a plain unique index instead of
    a NULL-safe workaround."""

    __tablename__ = "material_rate"
    __table_args__ = (
        Index(
            "uq_one_current_rate_per_point_material",
            "material_id",
            "collection_point_id",
            unique=True,
            postgresql_where=text("effective_to IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("material.id"), nullable=False)
    collection_point_id: Mapped[int] = mapped_column(
        ForeignKey("collection_point.id"), nullable=False
    )
    rate: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
