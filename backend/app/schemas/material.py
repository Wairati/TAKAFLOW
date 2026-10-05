from datetime import datetime

from pydantic import BaseModel


class MaterialCreate(BaseModel):
    name: str
    unit: str
    selling_rate: float | None = None


class MaterialUpdate(BaseModel):
    name: str | None = None
    unit: str | None = None
    is_active: bool | None = None
    selling_rate: float | None = None


class MaterialOut(BaseModel):
    id: int
    name: str
    unit: str
    is_active: bool
    selling_rate: float | None

    model_config = {"from_attributes": True}


class MaterialRateOut(BaseModel):
    id: int
    material_id: int
    collection_point_id: int
    grade: str | None
    rate: float
    effective_from: datetime
    effective_to: datetime | None

    model_config = {"from_attributes": True}


class AcceptMaterialRequest(BaseModel):
    """POST .../materials: start accepting a material at a branch, at this
    rate. `grade` is optional free text (e.g. "Grade A") — leave unset for a
    material's plain/ungraded rate; call this again with a different grade
    to add another price tier for the same material."""

    material_id: int
    rate: float
    grade: str | None = None


class SetRateRequest(BaseModel):
    """Which existing tier to rotate to a new rate — `grade` must match an
    already-accepted tier (None means the ungraded one)."""

    rate: float
    grade: str | None = None


class AcceptedMaterialOut(BaseModel):
    """One row of 'materials accepted at this branch, with every current
    price tier' — the §08 challenge-3 view. `rates` has one entry per grade
    currently offered (or a single ungraded entry if this material isn't
    graded at all)."""

    material: MaterialOut
    rates: list[MaterialRateOut]
