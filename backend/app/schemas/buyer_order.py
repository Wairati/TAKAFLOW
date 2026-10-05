from datetime import datetime

from pydantic import BaseModel, field_validator

from app.core.validation import validate_phone_number
from app.models.buyer_order import BuyerOrderStatus
from app.models.payment import PaymentMethod


class BuyerOrderCreate(BaseModel):
    buyer_name: str
    buyer_phone: str | None = None
    material_id: int
    quantity_requested: float
    notes: str | None = None
    # Required when an admin creates the order (there's no "their own branch"
    # to default to); ignored for staff, whose own branch is always used.
    collection_point_id: int | None = None

    @field_validator("buyer_phone")
    @classmethod
    def _check_phone(cls, value: str | None) -> str | None:
        if not value:
            return value
        return validate_phone_number(value)


class BuyerOrderOut(BaseModel):
    id: int
    collection_point_id: int
    collection_point_name: str
    buyer_name: str
    buyer_phone: str | None
    material_id: int
    material_name: str
    unit: str
    quantity_requested: float
    status: BuyerOrderStatus
    notes: str | None
    created_by_user_id: int
    created_at: datetime


class BuyerOrderPaymentCreate(BaseModel):
    """No `amount` field: the amount is computed server-side from the
    material's selling_rate * the order's quantity_requested (see
    buyer_order_service.record_payment) rather than typed in freely."""

    method: PaymentMethod
    reference_number: str | None = None


class BuyerOrderPaymentOut(BaseModel): #this is the output schema for a payment associated with a buyer order
    id: int
    buyer_order_id: int
    amount: float
    method: PaymentMethod
    reference_number: str | None
    recorded_by_user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
