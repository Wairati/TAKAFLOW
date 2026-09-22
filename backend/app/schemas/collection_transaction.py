import uuid
from datetime import datetime

from pydantic import BaseModel


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
    occurred_at: datetime | None = None  # defaults to server "now" if omitted


class CollectionTransactionOut(BaseModel):
    id: int
    client_transaction_uuid: uuid.UUID
    collection_point_id: int
    material_id: int
    material_rate_id: int
    rate: float
    recorded_by_user_id: int
    quantity: float
    grade: str | None
    collector_name: str | None
    collector_phone: str | None
    occurred_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
