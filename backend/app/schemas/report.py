from datetime import date

from pydantic import BaseModel


class MaterialTotal(BaseModel):
    material_id: int
    material_name: str
    quantity: float


class ReportsSummaryOut(BaseModel):
    # None means "every active branch combined" - only ever set that way for
    # an admin request; staff are always scoped to their own single branch.
    collection_point_id: int | None
    from_date: date
    to_date: date

    total_collected_quantity: float
    collected_by_material: list[MaterialTotal]

    total_sold_quantity: float
    sold_by_material: list[MaterialTotal]

    total_payments_amount: float


class DailyPoint(BaseModel):
    day: date
    collected_quantity: float
    sold_quantity: float
    payments_amount: float


class ReportsTimeseriesOut(BaseModel):
    collection_point_id: int | None
    from_date: date
    to_date: date
    points: list[DailyPoint]


class BranchTotal(BaseModel):
    collection_point_id: int
    collection_point_name: str
    collected_quantity: float
    sold_quantity: float
    payments_amount: float


class ReportsByBranchOut(BaseModel):
    from_date: date
    to_date: date
    branches: list[BranchTotal]
