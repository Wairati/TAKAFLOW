from datetime import datetime

from pydantic import BaseModel


class InventorySummaryOut(BaseModel):
    collection_point_id: int
    material_id: int
    material_name: str
    unit: str
    quantity_on_hand: float
    quantity_reserved: float
    updated_at: datetime


class InventorySaleCreate(BaseModel):
    material_id: int
    quantity: float
    sold_to: str | None = None


class InventorySaleOut(BaseModel):
    id: int
    collection_point_id: int
    material_id: int
    quantity: float
    sold_to: str | None
    recorded_by_user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
