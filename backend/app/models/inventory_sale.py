from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class InventorySale(TimestampMixin, Base):
    """One outbound movement of material out of a branch — the counterpart to
    CollectionTransaction (inbound). No buyer entity, matching the existing
    no-supplier-entity approach for collectors (SS25 item 7): `sold_to` is
    optional free text, not a foreign key. Posts a SALE row to the same
    inventory ledger a collection posts to (app.services.inventory_service)."""

    __tablename__ = "inventory_sale"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_point_id: Mapped[int] = mapped_column(ForeignKey("collection_point.id"), nullable=False)
    material_id: Mapped[int] = mapped_column(ForeignKey("material.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    sold_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recorded_by_user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
