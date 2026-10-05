import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.payment import PaymentMethod


class BuyerOrderStatus(str, enum.Enum):
    """OPEN -> PAID (a payment against the order has been recorded — recording
    it is itself the approval, no separate verification step) is the whole
    lifecycle. CANCELLED is only reachable from OPEN."""

    OPEN = "open"
    PAID = "paid"
    CANCELLED = "cancelled"


class BuyerOrder(TimestampMixin, Base):
    """A standing request from an external buyer for a quantity of one
    material, fulfilled from one branch's stock. Recording the buyer's
    payment both approves the order and decrements that branch's inventory
    in the same step — handing the material over physically happens outside
    the system."""

    __tablename__ = "buyer_order"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_point_id: Mapped[int] = mapped_column(ForeignKey("collection_point.id"), nullable=False)
    buyer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    buyer_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("material.id"), nullable=False)
    quantity_requested: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[BuyerOrderStatus] = mapped_column(
        Enum(BuyerOrderStatus, name="buyer_order_status"), nullable=False, default=BuyerOrderStatus.OPEN
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BuyerOrderPayment(TimestampMixin, Base):
    """Money IN from a buyer for an order — the reverse-direction counterpart
    of Payment (money OUT to a collector). Recorded by staff or an admin;
    recording it is itself the approval, immediately moving the order to
    PAID."""

    __tablename__ = "buyer_order_payment"

    id: Mapped[int] = mapped_column(primary_key=True)
    buyer_order_id: Mapped[int] = mapped_column(ForeignKey("buyer_order.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, name="payment_method"), nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recorded_by_user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
