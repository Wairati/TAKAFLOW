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
            username="admin.test",
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
            employee_number="900001",
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


def _login(identifier: str, password: str) -> dict:
    response = client.post("/api/v1/auth/login", json={"identifier": identifier, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def test_login_success(admin_user):
    tokens = _login("admin.test@example.com", ADMIN_PASSWORD)
    assert "access_token" in tokens
    assert "refresh_token" in tokens


def test_login_with_username(admin_user):
    tokens = _login("admin.test", ADMIN_PASSWORD)
    assert "access_token" in tokens
    assert "refresh_token" in tokens


def test_login_wrong_password(admin_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin.test@example.com", "password": "wrong-password"},
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
            "employee_number": "100001",
            "password": "Newstaff1!",
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
            "employee_number": "100002",
            "password": "Newstaff2!",
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


def test_login_with_employee_number(staff_user):
    tokens = _login("900001", STAFF_PASSWORD)
    assert "access_token" in tokens
    assert "refresh_token" in tokens


def _create_user_payload(**overrides) -> dict:
    payload = {
        "email": "format.check@example.com",
        "employee_number": "200001",
        "password": "Valid1pass!",
        "full_name": "Format Check",
        "role": "collection_point_staff",
    }
    payload.update(overrides)
    return payload


def test_create_user_rejects_malformed_employee_number(admin_user):
    tokens = _login("admin.test@example.com", ADMIN_PASSWORD)
    response = client.post(
        "/api/v1/auth/users",
        json=_create_user_payload(employee_number="12AB56"),
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 422


def test_create_user_rejects_wrong_length_employee_number(admin_user):
    tokens = _login("admin.test@example.com", ADMIN_PASSWORD)
    response = client.post(
        "/api/v1/auth/users",
        json=_create_user_payload(employee_number="12345"),
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 422


def test_create_staff_requires_employee_number(admin_user):
    tokens = _login("admin.test@example.com", ADMIN_PASSWORD)
    response = client.post(
        "/api/v1/auth/users",
        json=_create_user_payload(employee_number=None),
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "bad_password",
    [
        "alllowercase1!",  # no uppercase, and too long (14 chars)
        "NOLOWERCASE1!",  # no lowercase
        "NoDigitsHere!",  # no digit
        "NoSpecial123",  # no special character
        "Ab1!",  # too short
        "ThisPassword1!IsTooLong",  # too long
    ],
)
def test_create_user_rejects_weak_password(admin_user, bad_password):
    tokens = _login("admin.test@example.com", ADMIN_PASSWORD)
    response = client.post(
        "/api/v1/auth/users",
        json=_create_user_payload(password=bad_password),
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 422, f"expected rejection for password: {bad_password!r}"


def test_create_user_duplicate_employee_number(admin_user):
    tokens = _login("admin.test@example.com", ADMIN_PASSWORD)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    first = client.post(
        "/api/v1/auth/users",
        json=_create_user_payload(email="dup.one@example.com", employee_number="300001"),
        headers=headers,
    )
    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/auth/users",
        json=_create_user_payload(email="dup.two@example.com", employee_number="300001"),
        headers=headers,
    )
    assert second.status_code == 409

    with SessionLocal() as db:
        db.query(User).filter(User.email == "dup.one@example.com").delete()
        db.commit()


@pytest.mark.parametrize(
    "bad_name",
    ["12345", "John123", "4", "!!!"],
)
def test_create_user_rejects_invalid_full_name(admin_user, bad_name):
    tokens = _login("admin.test@example.com", ADMIN_PASSWORD)
    response = client.post(
        "/api/v1/auth/users",
        json=_create_user_payload(full_name=bad_name),
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 422, f"expected rejection for full_name: {bad_name!r}"


def test_create_user_accepts_hyphenated_apostrophe_name(admin_user):
    tokens = _login("admin.test@example.com", ADMIN_PASSWORD)
    response = client.post(
        "/api/v1/auth/users",
        json=_create_user_payload(email="ok.name@example.com", employee_number="400002", full_name="Mary-Jane O'Brien"),
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 201, response.text

    with SessionLocal() as db:
        db.query(User).filter(User.email == "ok.name@example.com").delete()
        db.commit()


def test_list_users_requires_admin(staff_user):
    tokens = _login("staff.test@example.com", STAFF_PASSWORD)
    response = client.get("/api/v1/auth/users", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert response.status_code == 403


def test_list_users_as_admin(admin_user, staff_user):
    tokens = _login("admin.test@example.com", ADMIN_PASSWORD)
    response = client.get("/api/v1/auth/users", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert response.status_code == 200
    emails = [u["email"] for u in response.json()]
    assert "staff.test@example.com" in emails
    assert "admin.test@example.com" in emails


def test_deactivate_blocks_login(admin_user, staff_user):
    admin_tokens = _login("admin.test@example.com", ADMIN_PASSWORD)
    admin_headers = {"Authorization": f"Bearer {admin_tokens['access_token']}"}

    deactivate = client.post(f"/api/v1/auth/users/{staff_user}/deactivate", headers=admin_headers)
    assert deactivate.status_code == 200, deactivate.text
    assert deactivate.json()["is_active"] is False

    blocked = client.post(
        "/api/v1/auth/login", json={"identifier": "staff.test@example.com", "password": STAFF_PASSWORD}
    )
    assert blocked.status_code == 401

    reactivate = client.post(f"/api/v1/auth/users/{staff_user}/reactivate", headers=admin_headers)
    assert reactivate.status_code == 200
    assert reactivate.json()["is_active"] is True

    restored = client.post(
        "/api/v1/auth/login", json={"identifier": "staff.test@example.com", "password": STAFF_PASSWORD}
    )
    assert restored.status_code == 200


def test_deactivate_revokes_existing_refresh_token(admin_user, staff_user):
    admin_tokens = _login("admin.test@example.com", ADMIN_PASSWORD)
    admin_headers = {"Authorization": f"Bearer {admin_tokens['access_token']}"}
    staff_tokens = _login("staff.test@example.com", STAFF_PASSWORD)

    client.post(f"/api/v1/auth/users/{staff_user}/deactivate", headers=admin_headers)

    refresh_attempt = client.post("/api/v1/auth/refresh", json={"refresh_token": staff_tokens["refresh_token"]})
    assert refresh_attempt.status_code == 401

    client.post(f"/api/v1/auth/users/{staff_user}/reactivate", headers=admin_headers)


def test_admin_cannot_deactivate_self(admin_user):
    tokens = _login("admin.test@example.com", ADMIN_PASSWORD)
    response = client.post(
        f"/api/v1/auth/users/{admin_user}/deactivate", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 400


def test_reset_password_requires_admin(staff_user):
    tokens = _login("staff.test@example.com", STAFF_PASSWORD)
    response = client.post(
        f"/api/v1/auth/users/{staff_user}/reset-password",
        json={"new_password": "NewPass1!"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 403


def test_reset_password_changes_credential(admin_user, staff_user):
    admin_tokens = _login("admin.test@example.com", ADMIN_PASSWORD)
    admin_headers = {"Authorization": f"Bearer {admin_tokens['access_token']}"}

    response = client.post(
        f"/api/v1/auth/users/{staff_user}/reset-password",
        json={"new_password": "NewPass1!"},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text

    old_password_attempt = client.post(
        "/api/v1/auth/login", json={"identifier": "staff.test@example.com", "password": STAFF_PASSWORD}
    )
    assert old_password_attempt.status_code == 401

    new_password_attempt = client.post(
        "/api/v1/auth/login", json={"identifier": "staff.test@example.com", "password": "NewPass1!"}
    )
    assert new_password_attempt.status_code == 200


def test_reset_password_revokes_existing_refresh_token(admin_user, staff_user):
    admin_tokens = _login("admin.test@example.com", ADMIN_PASSWORD)
    admin_headers = {"Authorization": f"Bearer {admin_tokens['access_token']}"}
    staff_tokens = _login("staff.test@example.com", STAFF_PASSWORD)

    client.post(
        f"/api/v1/auth/users/{staff_user}/reset-password",
        json={"new_password": "NewPass1!"},
        headers=admin_headers,
    )

    refresh_attempt = client.post("/api/v1/auth/refresh", json={"refresh_token": staff_tokens["refresh_token"]})
    assert refresh_attempt.status_code == 401


def test_reset_password_rejects_weak_password(admin_user, staff_user):
    tokens = _login("admin.test@example.com", ADMIN_PASSWORD)
    response = client.post(
        f"/api/v1/auth/users/{staff_user}/reset-password",
        json={"new_password": "weak"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 422
