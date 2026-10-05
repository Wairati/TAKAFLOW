from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Partner(TimestampMixin, Base):
    """An environmental/conservation organisation the company collaborates
    with. A collection tagged with a partner (CollectionTransaction.partner_id)
    is logged without expecting a supplier payment — see
    collection_transaction_service.record_collection."""

    __tablename__ = "partner"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
