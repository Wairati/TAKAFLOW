from pydantic import BaseModel, EmailStr, field_validator, model_validator

from app.core.validation import validate_employee_number, validate_full_name, validate_password_complexity
from app.models.user import UserRole


class LoginRequest(BaseModel):
    # The account's email, username, or (for collection-point staff) employee
    # number — auth_service.authenticate matches against all three columns.
    identifier: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str | None
    employee_number: str | None
    full_name: str
    role: UserRole
    collection_point_id: int | None
    is_active: bool

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    username: str | None = None
    # Required for COLLECTION_POINT_STAFF (the collection-app's login screen
    # only ever collects this field); left unset for admins.
    employee_number: str | None = None
    password: str
    full_name: str
    role: UserRole
    collection_point_id: int | None = None

    @field_validator("full_name")
    @classmethod
    def _check_full_name(cls, value: str) -> str:
        return validate_full_name(value)

    @field_validator("employee_number")
    @classmethod
    def _check_employee_number_format(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_employee_number(value)

    @field_validator("password")
    @classmethod
    def _check_password_complexity(cls, value: str) -> str:
        return validate_password_complexity(value)

    @model_validator(mode="after")
    def _require_employee_number_for_staff(self) -> "UserCreate":
        if self.role == UserRole.COLLECTION_POINT_STAFF and not self.employee_number:
            raise ValueError("employee_number is required for collection point staff")
        return self


class ResetPasswordRequest(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _check_password_complexity(cls, value: str) -> str:
        return validate_password_complexity(value)
