from datetime import date

from pydantic import BaseModel


class MaterialTotal(BaseModel):
    material_id: int
    material_name: str
    quantity: float


class ReportsSummaryOut(BaseModel):
    collection_point_id: int
    from_date: date
    to_date: date

    total_collected_quantity: float
    collected_by_material: list[MaterialTotal]

    total_sold_quantity: float
    sold_by_material: list[MaterialTotal]

    total_payments_amount: float
