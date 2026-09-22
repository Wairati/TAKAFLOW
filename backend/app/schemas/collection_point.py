from pydantic import BaseModel


class CollectionPointCreate(BaseModel):
    name: str
    address: str
    county: str
    latitude: float | None = None
    longitude: float | None = None
    opening_hours: str | None = None


class CollectionPointUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    county: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    opening_hours: str | None = None
    is_active: bool | None = None


class CollectionPointOut(BaseModel):
    id: int
    name: str
    address: str
    county: str
    latitude: float | None
    longitude: float | None
    opening_hours: str | None
    is_active: bool

    model_config = {"from_attributes": True}
