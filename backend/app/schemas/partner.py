from pydantic import BaseModel, field_validator

from app.core.validation import validate_phone_number


class PartnerCreate(BaseModel):
    name: str
    contact_person: str | None = None
    phone: str | None = None

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, value: str | None) -> str | None:
        if not value:
            return value
        return validate_phone_number(value)


class PartnerUpdate(BaseModel):
    name: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    is_active: bool | None = None

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, value: str | None) -> str | None:
        if not value:
            return value
        return validate_phone_number(value)


class PartnerOut(BaseModel):
    id: int
    name: str
    contact_person: str | None
    phone: str | None
    is_active: bool

    model_config = {"from_attributes": True}
