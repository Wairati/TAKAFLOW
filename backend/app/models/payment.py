import enum

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class PaymentMethod(str, enum.Enum):
    """§25 item 2: manual recording only — no live Daraja disbursement."""

    MPESA = "mpesa"
    CASH = "cash"


class Payment(TimestampMixin, Base):
    """One payout to a collector. FK is one-to-many against the transaction
    (§08) in case a single delivery is ever split across two payments."""

    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_transaction_id: Mapped[int] = mapped_column(
        ForeignKey("collection_transaction.id"), nullable=False
    )

    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
