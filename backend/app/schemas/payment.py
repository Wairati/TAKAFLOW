from datetime import datetime

from pydantic import BaseModel

from app.models.payment import PaymentMethod


class PaymentCreate(BaseModel):
    method: PaymentMethod
    amount: float
    reference_number: str | None = None


class PaymentOut(BaseModel):
    id: int
    collection_transaction_id: int
    method: PaymentMethod
    amount: float
    reference_number: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
