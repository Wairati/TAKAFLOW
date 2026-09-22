from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
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
from app.models.user import User
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


def authenticate(db: Session, email: str, password: str) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
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

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
        collection_point_id=data.collection_point_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
