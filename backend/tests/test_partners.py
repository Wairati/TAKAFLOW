"""Admin CRUD for partner organisations — the managed list staff pick from
when logging a collaborative (unpaid) collection. Against the real database."""

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.partner import Partner
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole

client = TestClient(app)

ADMIN_PASSWORD = "admin-test-password-123"
STAFF_PASSWORD = "staff-test-password-123"


def _login(identifier: str, password: str) -> dict:
    response = client.post("/api/v1/auth/login", json={"identifier": identifier, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin_headers():
    with SessionLocal() as db:
        user = User(
            email="partners.admin@example.com", hashed_password=hash_password(ADMIN_PASSWORD),
            full_name="Partners Admin", role=UserRole.ADMIN,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    yield _login("partners.admin@example.com", ADMIN_PASSWORD)

    with SessionLocal() as db:
        db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


@pytest.fixture
def staff_headers():
    with SessionLocal() as db:
        user = User(
            email="partners.staff@example.com", hashed_password=hash_password(STAFF_PASSWORD),
            full_name="Partners Staff", role=UserRole.COLLECTION_POINT_STAFF, employee_number="920001",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    yield _login("920001", STAFF_PASSWORD)

    with SessionLocal() as db:
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


@pytest.fixture
def partner(admin_headers):
    response = client.post(
        "/api/v1/partners",
        json={"name": "Green Earth Collective", "contact_person": "Aisha Noor", "phone": "0711223344"},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    partner_id = response.json()["id"]
    yield partner_id
    with SessionLocal() as db:
        db.query(Partner).filter(Partner.id == partner_id).delete()
        db.commit()


def test_admin_can_create_partner(admin_headers):
    response = client.post(
        "/api/v1/partners", json={"name": "River Cleanup Trust"}, headers=admin_headers
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "River Cleanup Trust"
    assert body["is_active"] is True

    with SessionLocal() as db:
        db.query(Partner).filter(Partner.id == body["id"]).delete()
        db.commit()


def test_staff_cannot_create_partner(staff_headers):
    response = client.post("/api/v1/partners", json={"name": "Should Fail"}, headers=staff_headers)
    assert response.status_code == 403


def test_duplicate_partner_name_rejected(admin_headers, partner):
    response = client.post(
        "/api/v1/partners", json={"name": "Green Earth Collective"}, headers=admin_headers
    )
    assert response.status_code == 409


def test_staff_can_list_partners(staff_headers, partner):
    response = client.get("/api/v1/partners", headers=staff_headers)
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert "Green Earth Collective" in names


def test_admin_can_deactivate_partner(admin_headers, partner):
    response = client.patch(f"/api/v1/partners/{partner}", json={"is_active": False}, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_get_unknown_partner_is_404(admin_headers):
    response = client.get("/api/v1/partners/999999999", headers=admin_headers)
    assert response.status_code == 404
