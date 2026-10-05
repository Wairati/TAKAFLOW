import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.core.validation import validate_phone_number


class CollectionTransactionCreate(BaseModel):
    # Client-generated idempotency key (SS10) — required even for this
    # online-only phase, so the field never needs to change when Phase 8's
    # offline outbox starts generating it on a device instead of a browser tab.
    client_transaction_uuid: uuid.UUID

    material_id: int
    quantity: float
    grade: str | None = None
    collector_name: str | None = None
    collector_phone: str | None = None
    # Set for a collaborative collection contributed by a partner
    # organisation — skips the rate lookup entirely, and no payment is ever
    # expected or allowed against the resulting transaction.
    partner_id: int | None = None
    occurred_at: datetime | None = None  # defaults to server "now" if omitted

    @field_validator("collector_phone")
    @classmethod
    def _check_phone(cls, value: str | None) -> str | None:
        if not value:
            return value
        return validate_phone_number(value)


class CollectionTransactionOut(BaseModel):
    id: int
    client_transaction_uuid: uuid.UUID
    collection_point_id: int
    material_id: int
    material_rate_id: int | None
    rate: float | None
    recorded_by_user_id: int
    quantity: float
    grade: str | None
    collector_name: str | None
    collector_phone: str | None
    partner_id: int | None
    occurred_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
