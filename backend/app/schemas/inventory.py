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
