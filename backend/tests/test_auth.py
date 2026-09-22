"""§19: Auth/RBAC tests — hitting real routes with real (test) users, not mocks.
Each fixture creates rows in the real dev database and deletes them afterward."""

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole

client = TestClient(app)

ADMIN_PASSWORD = "admin-test-password-123"
STAFF_PASSWORD = "staff-test-password-123"


@pytest.fixture
def admin_user():
    with SessionLocal() as db:
        user = User(
            email="admin.test@example.com",
            hashed_password=hash_password(ADMIN_PASSWORD),
            full_name="Test Admin",
            role=UserRole.ADMIN,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    yield user_id
    with SessionLocal() as db:
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


@pytest.fixture
def staff_user():
    with SessionLocal() as db:
        user = User(
            email="staff.test@example.com",
            hashed_password=hash_password(STAFF_PASSWORD),
            full_name="Test Staff",
            role=UserRole.COLLECTION_POINT_STAFF,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    yield user_id
    with SessionLocal() as db:
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


def _login(email: str, password: str) -> dict:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def test_login_success(admin_user):
    tokens = _login("admin.test@example.com", ADMIN_PASSWORD)
    assert "access_token" in tokens
    assert "refresh_token" in tokens


def test_login_wrong_password(admin_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin.test@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_me_requires_credentials():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401  # HTTPBearer's own "not authenticated" response


def test_me_rejects_garbage_token():
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_me_with_valid_token(admin_user):
    tokens = _login("admin.test@example.com", ADMIN_PASSWORD)
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "admin.test@example.com"
    assert body["role"] == "admin"


def test_refresh_rotates_token(admin_user):
    tokens = _login("admin.test@example.com", ADMIN_PASSWORD)

    refreshed = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # The original refresh token was single-use — replaying it must fail.
    replay = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert replay.status_code == 401


def test_create_user_requires_admin_role(staff_user):
    tokens = _login("staff.test@example.com", STAFF_PASSWORD)
    response = client.post(
        "/api/v1/auth/users",
        json={
            "email": "someone.new@example.com",
            "password": "irrelevant-123",
            "full_name": "Someone New",
            "role": "collection_point_staff",
        },
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 403


def test_create_user_as_admin(admin_user):
    tokens = _login("admin.test@example.com", ADMIN_PASSWORD)
    response = client.post(
        "/api/v1/auth/users",
        json={
            "email": "new.staff@example.com",
            "password": "new-staff-password-123",
            "full_name": "New Staff",
            "role": "collection_point_staff",
        },
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["email"] == "new.staff@example.com"

    with SessionLocal() as db:
        db.query(User).filter(User.email == "new.staff@example.com").delete()
        db.commit()
