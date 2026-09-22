from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class every ORM model inherits from; used by Alembic for autogenerate."""
