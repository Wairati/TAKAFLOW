from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy import update as sql_update
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole
from app.schemas.auth import TokenResponse, UserCreate


def _issue_token_pair(db: Session, user: User) -> TokenResponse:
    access_token = create_access_token(user.id, user.role.value)

    raw_refresh_token = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh_token),
            expires_at=refresh_token_expiry(),
        )
    )
    db.commit()

    return TokenResponse(access_token=access_token, refresh_token=raw_refresh_token)


def authenticate(db: Session, identifier: str, password: str) -> TokenResponse:
    user = db.scalar(
        select(User).where(
            or_(
                User.email == identifier,
                User.username == identifier,
                User.employee_number == identifier,
            )
        )
    )
    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return _issue_token_pair(db, user)


def refresh(db: Session, raw_refresh_token: str) -> TokenResponse:
    """Rotation (ADR-04): the presented token is revoked and a brand new one
    issued, whether or not this request turns out to be legitimate reuse of an
    already-revoked token — that reuse is itself a signal worth catching later,
    but for now we simply never let one refresh token be used twice."""
    token_hash = hash_refresh_token(raw_refresh_token)
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
    )
    if stored is None or stored.revoked_at is not None:
        raise invalid
    if stored.expires_at < datetime.now(timezone.utc):
        raise invalid

    stored.revoked_at = datetime.now(timezone.utc)
    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        db.commit()
        raise invalid

    return _issue_token_pair(db, user)


def revoke(db: Session, raw_refresh_token: str) -> None:
    token_hash = hash_refresh_token(raw_refresh_token)
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(timezone.utc)
        db.commit()


def create_user(db: Session, data: UserCreate) -> User:
    if db.scalar(select(User).where(User.email == data.email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    if data.username is not None and db.scalar(select(User).where(User.username == data.username)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    if (
        data.employee_number is not None
        and db.scalar(select(User).where(User.employee_number == data.employee_number)) is not None
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee number already in use")

    user = User(
        email=data.email,
        username=data.username,
        employee_number=data.employee_number,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
        collection_point_id=data.collection_point_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(
    db: Session, *, role: UserRole | None = None, collection_point_id: int | None = None
) -> list[User]:
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if collection_point_id is not None:
        stmt = stmt.where(User.collection_point_id == collection_point_id)
    stmt = stmt.order_by(User.full_name)
    return list(db.scalars(stmt))


def set_active(db: Session, user_id: int, is_active: bool) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_active = is_active
    if not is_active:
        # Deactivating only blocks future logins/refreshes (authenticate and
        # refresh both already check is_active) - also revoke every
        # outstanding refresh token so an already-logged-in session can't
        # just refresh its way to a new access token afterward. The current
        # access token, if any, still expires naturally on its own short TTL.
        db.execute(
            sql_update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
    db.commit()
    db.refresh(user)
    return user


def reset_password(db: Session, user_id: int, new_password: str) -> User:
    """Admin-mediated reset - there's no self-service "forgot password" flow
    (no email sending is set up), so this is the actual answer to "someone
    forgot their password": an admin sets a new one for them here. Revokes
    every outstanding refresh token, same reasoning as deactivating - a
    session that predates the reset shouldn't be able to keep refreshing on
    the old credential's trust."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.hashed_password = hash_password(new_password)
    db.execute(
        sql_update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    db.commit()
    db.refresh(user)
    return user
