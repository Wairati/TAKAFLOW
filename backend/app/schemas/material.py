from datetime import datetime

from pydantic import BaseModel


class MaterialCreate(BaseModel):
    name: str
    unit: str


class MaterialUpdate(BaseModel):
    name: str | None = None
    unit: str | None = None
    is_active: bool | None = None


class MaterialOut(BaseModel):
    id: int
    name: str
    unit: str
    is_active: bool

    model_config = {"from_attributes": True}


class MaterialRateOut(BaseModel):
    id: int
    material_id: int
    collection_point_id: int
    rate: float
    effective_from: datetime
    effective_to: datetime | None

    model_config = {"from_attributes": True}


class AcceptMaterialRequest(BaseModel):
    """POST .../materials: start accepting a material at a branch, at this rate."""

    material_id: int
    rate: float


class SetRateRequest(BaseModel):
    rate: float


class AcceptedMaterialOut(BaseModel):
    """One row of 'materials accepted at this branch, with the current rate' —
    the §08 challenge-3 view: the eventual public-site source of truth."""

    material: MaterialOut
    current_rate: MaterialRateOut
