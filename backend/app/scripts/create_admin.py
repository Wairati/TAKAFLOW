"""One-time bootstrap: there's no self-registration (§06 — accounts are
provisioned, not signed up for), so the very first admin has to be created
directly against the database, outside the API. Every admin after this one
should be created via POST /auth/users instead.

Usage (from backend/, with the venv active):
    python -m app.scripts.create_admin
"""

import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User, UserRole


def main() -> None:
    email = input("Admin email: ").strip()
    full_name = input("Full name: ").strip()
    password = getpass.getpass("Password: ")

    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)) is not None:
            print(f"A user with email {email} already exists.")
            return

        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=UserRole.ADMIN,
            collection_point_id=None,
        )
        db.add(user)
        db.commit()
        print(f"Created admin user: {email}")


if __name__ == "__main__":
    main()
