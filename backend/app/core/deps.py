from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole

_bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """§14: every protected route depends on this to decode the token and load
    the current user's role and scope. Enforcement happens here, server-side —
    the only enforcement that actually matters (§06)."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise unauthorized

    user_id = payload.get("sub")
    if user_id is None:
        raise unauthorized

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise unauthorized

    return user


def require_role(*allowed_roles: UserRole):
    """§14: `require_role("admin")` as a per-route dependency, not a check
    scattered inside handler bodies."""

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return checker


def require_own_collection_point(collection_point_id: int, current_user: User = Depends(get_current_user)) -> User:
    """§06: row-level scoping, not just role-level — a staff member can only
    touch resources at their own branch. Admins are exempt (not scoped to one
    branch)."""
    if current_user.role == UserRole.ADMIN:
        return current_user
    if current_user.collection_point_id != collection_point_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this collection point",
        )
    return current_user
