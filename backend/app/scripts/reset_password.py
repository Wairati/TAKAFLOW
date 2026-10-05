"""Resets an account's password directly against the database. This is for
the one case the admin-portal's own "Reset password" action can't cover: an
admin locked out of their own account, with no other admin around to reset
it for them (or before any staff/admin accounts exist to click anything).
For every other case - staff forgetting a password - use the admin-portal's
Staff page instead; it calls the same underlying logic over the API.

Also revokes every outstanding refresh token for the account, same as the
API-driven reset does, so an old session can't keep refreshing past this.

Usage (from backend/, with the venv active):
    python -m app.scripts.reset_password
"""

import getpass
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy import update as sql_update

from app.core.security import hash_password
from app.core.validation import validate_password_complexity
from app.db.session import SessionLocal
from app.models.refresh_token import RefreshToken
from app.models.user import User


def main() -> None:
    identifier = input("Email, username, or employee number of the account to reset: ").strip()

    while True:
        password = getpass.getpass("New password (8-12 chars, upper+lower+digit+special !@#$%^&*): ")
        try:
            validate_password_complexity(password)
            break
        except ValueError as exc:
            print(f"  {exc} — try again.")

    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(
                or_(User.email == identifier, User.username == identifier, User.employee_number == identifier)
            )
        )
        if user is None:
            print(f"No account found matching {identifier!r}.")
            return

        user.hashed_password = hash_password(password)
        db.execute(
            sql_update(RefreshToken)
            .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        db.commit()
        print(f"Password reset for {user.full_name} ({user.email}).")


if __name__ == "__main__":
    main()
