import enum
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    """§06: only the roles this build actually uses. BUYER is future scope —
    adding it later is one new enum value, not a redesign."""

    ADMIN = "admin"
    COLLECTION_POINT_STAFF = "collection_point_staff"


class User(TimestampMixin, Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # Optional second login identifier alongside email (login accepts either).
    # Nullable so existing/admin-provisioned accounts aren't forced to have one.
    username: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    # Collection-point staff log in with this instead of email/username (the
    # collection-app's login screen only ever collects this field). Nullable
    # at the DB level since admins don't have one — required-for-staff is
    # enforced in UserCreate, not here.
    employee_number: Mapped[str | None] = mapped_column(String(6), unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)

    # Row-level scoping (§06): staff can only touch their own branch's data.
    # NULL for admins, who aren't scoped to one branch.
    collection_point_id: Mapped[int | None] = mapped_column(
        ForeignKey("collection_point.id"), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)

    collection_point: Mapped["CollectionPoint | None"] = relationship(back_populates="staff")
