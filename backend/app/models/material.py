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
    # What we charge a buyer per unit of this material. Nullable: a material
    # with no selling rate set yet simply can't have a buyer-order payment
    # recorded against it (see buyer_order_service.record_payment) until an
    # admin sets one. Unlike MaterialRate, this isn't branch/grade-scoped or
    # time-stamped — buyer pricing is one flat rate per material.
    selling_rate: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)


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
    to a specific branch (no NULL/'global default' row).

    `grade` is optional free text an admin sets per material (e.g. "Grade A"),
    not a fixed system-wide list - a material can have one ungraded rate
    (grade IS NULL), several graded rates, or both at once. "Exactly one
    current rate" therefore needs two partial indexes rather than one: NULL
    grades don't collide with each other under a plain unique index (Postgres
    treats every NULL as distinct), so the ungraded case is enforced by its
    own index scoped to `grade IS NULL`, separate from the graded case."""

    __tablename__ = "material_rate"
    __table_args__ = (
        Index(
            "uq_one_current_ungraded_rate",
            "material_id",
            "collection_point_id",
            unique=True,
            postgresql_where=text("effective_to IS NULL AND grade IS NULL"),
        ),
        Index(
            "uq_one_current_graded_rate",
            "material_id",
            "collection_point_id",
            "grade",
            unique=True,
            postgresql_where=text("effective_to IS NULL AND grade IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("material.id"), nullable=False)
    collection_point_id: Mapped[int] = mapped_column(
        ForeignKey("collection_point.id"), nullable=False
    )
    grade: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rate: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
