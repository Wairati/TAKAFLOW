"""§19: admin CRUD for materials/collection points, and the rate-rotation
logic from §08 challenge 2 — proven against the real database."""

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.collection_point import CollectionPoint
from app.models.material import CollectionPointMaterial, Material, MaterialRate
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole

client = TestClient(app)

ADMIN_PASSWORD = "admin-test-password-123"


@pytest.fixture
def admin_headers():
    with SessionLocal() as db:
        user = User(
            email="materials.admin@example.com",
            hashed_password=hash_password(ADMIN_PASSWORD),
            full_name="Materials Admin",
            role=UserRole.ADMIN,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    response = client.post(
        "/api/v1/auth/login", json={"identifier": "materials.admin@example.com", "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]

    yield {"Authorization": f"Bearer {token}"}

    with SessionLocal() as db:
        db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


@pytest.fixture
def material(admin_headers):
    response = client.post(
        "/api/v1/materials", json={"name": "Test PET Bottles", "unit": "kg"}, headers=admin_headers
    )
    assert response.status_code == 201, response.text
    material_id = response.json()["id"]
    yield material_id
    with SessionLocal() as db:
        db.query(MaterialRate).filter(MaterialRate.material_id == material_id).delete()
        db.query(CollectionPointMaterial).filter(CollectionPointMaterial.material_id == material_id).delete()
        db.query(Material).filter(Material.id == material_id).delete()
        db.commit()


@pytest.fixture
def point(admin_headers):
    response = client.post(
        "/api/v1/collection-points",
        json={"name": "Test Branch", "address": "1 Test Road", "county": "Nairobi"},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    point_id = response.json()["id"]
    yield point_id
    with SessionLocal() as db:
        db.query(MaterialRate).filter(MaterialRate.collection_point_id == point_id).delete()
        db.query(CollectionPointMaterial).filter(CollectionPointMaterial.collection_point_id == point_id).delete()
        db.query(CollectionPoint).filter(CollectionPoint.id == point_id).delete()
        db.commit()


def test_create_material_requires_admin():
    response = client.post("/api/v1/materials", json={"name": "X", "unit": "kg"})
    assert response.status_code == 401  # no credentials at all


def test_create_and_get_material(admin_headers, material):
    response = client.get(f"/api/v1/materials/{material}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Test PET Bottles"


def test_duplicate_material_name_conflict(admin_headers, material):
    response = client.post(
        "/api/v1/materials", json={"name": "Test PET Bottles", "unit": "kg"}, headers=admin_headers
    )
    assert response.status_code == 409


def test_accept_material_sets_current_rate(admin_headers, material, point):
    response = client.post(
        f"/api/v1/collection-points/{point}/materials",
        json={"material_id": material, "rate": 15.5},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body["rates"]) == 1
    assert body["rates"][0]["rate"] == 15.5
    assert body["rates"][0]["grade"] is None
    assert body["rates"][0]["effective_to"] is None


def test_accept_material_twice_for_same_grade_conflicts(admin_headers, material, point):
    client.post(
        f"/api/v1/collection-points/{point}/materials",
        json={"material_id": material, "rate": 15.5},
        headers=admin_headers,
    )
    response = client.post(
        f"/api/v1/collection-points/{point}/materials",
        json={"material_id": material, "rate": 20.0},
        headers=admin_headers,
    )
    assert response.status_code == 409


def test_material_can_have_multiple_graded_rates(admin_headers, material, point):
    client.post(
        f"/api/v1/collection-points/{point}/materials",
        json={"material_id": material, "rate": 10.0, "grade": "Grade A"},
        headers=admin_headers,
    )
    response = client.post(
        f"/api/v1/collection-points/{point}/materials",
        json={"material_id": material, "rate": 6.0, "grade": "Mixed"},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    rates_by_grade = {r["grade"]: r["rate"] for r in response.json()["rates"]}
    assert rates_by_grade == {"Grade A": 10.0, "Mixed": 6.0}


def test_change_rate_rotates_history(admin_headers, material, point):
    client.post(
        f"/api/v1/collection-points/{point}/materials",
        json={"material_id": material, "rate": 10.0},
        headers=admin_headers,
    )

    response = client.patch(
        f"/api/v1/collection-points/{point}/materials/{material}/rate",
        json={"rate": 12.0},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["rate"] == 12.0
    assert response.json()["effective_to"] is None

    history = client.get(
        f"/api/v1/collection-points/{point}/materials/{material}/rate-history", headers=admin_headers
    ).json()
    assert len(history) == 2
    rates_by_value = {row["rate"]: row for row in history}
    assert rates_by_value[10.0]["effective_to"] is not None  # closed out
    assert rates_by_value[12.0]["effective_to"] is None  # current


def test_change_rate_targets_the_right_grade(admin_headers, material, point):
    client.post(
        f"/api/v1/collection-points/{point}/materials",
        json={"material_id": material, "rate": 10.0, "grade": "Grade A"},
        headers=admin_headers,
    )
    client.post(
        f"/api/v1/collection-points/{point}/materials",
        json={"material_id": material, "rate": 6.0, "grade": "Mixed"},
        headers=admin_headers,
    )

    response = client.patch(
        f"/api/v1/collection-points/{point}/materials/{material}/rate",
        json={"rate": 11.0, "grade": "Grade A"},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["rate"] == 11.0
    assert response.json()["grade"] == "Grade A"

    accepted = client.get(f"/api/v1/collection-points/{point}/materials", headers=admin_headers).json()
    rates_by_grade = {r["grade"]: r["rate"] for r in accepted[0]["rates"]}
    assert rates_by_grade == {"Grade A": 11.0, "Mixed": 6.0}  # Mixed untouched


def test_stop_accepting_closes_rate_and_removes_link(admin_headers, material, point):
    client.post(
        f"/api/v1/collection-points/{point}/materials",
        json={"material_id": material, "rate": 10.0},
        headers=admin_headers,
    )

    response = client.delete(
        f"/api/v1/collection-points/{point}/materials/{material}", headers=admin_headers
    )
    assert response.status_code == 204

    accepted = client.get(f"/api/v1/collection-points/{point}/materials", headers=admin_headers).json()
    assert accepted == []

    history = client.get(
        f"/api/v1/collection-points/{point}/materials/{material}/rate-history", headers=admin_headers
    ).json()
    assert len(history) == 1
    assert history[0]["effective_to"] is not None
