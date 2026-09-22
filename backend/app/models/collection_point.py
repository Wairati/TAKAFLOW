from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class CollectionPoint(TimestampMixin, Base):
    """A physical branch. §02/§25 item 3: fixed premises, not a roaming field agent."""

    __tablename__ = "collection_point"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    county: Mapped[str] = mapped_column(String(100), nullable=False)

    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    opening_hours: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    staff: Mapped[list["User"]] = relationship(back_populates="collection_point")
