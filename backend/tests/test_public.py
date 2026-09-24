"""§05 / Phase 12: the public site's data source needs no auth, shows only
active branches, and hides an inactive branch's details entirely - the same
way a 404 would if it never existed."""

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
            email="public.admin@example.com", hashed_password=hash_password(ADMIN_PASSWORD),
            full_name="Public Admin", role=UserRole.ADMIN,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    response = client.post("/api/v1/auth/login", json={"identifier": "public.admin@example.com", "password": ADMIN_PASSWORD})
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    yield headers

    with SessionLocal() as db:
        db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


@pytest.fixture
def active_point_with_material(admin_headers):
    point_resp = client.post(
        "/api/v1/collection-points",
        json={"name": "Public Active Branch", "address": "1 Public Rd", "county": "Nairobi"},
        headers=admin_headers,
    )
    point_id = point_resp.json()["id"]
    material_resp = client.post(
        "/api/v1/materials", json={"name": "Public Test Material", "unit": "kg"}, headers=admin_headers
    )
    material_id = material_resp.json()["id"]
    client.post(
        f"/api/v1/collection-points/{point_id}/materials",
        json={"material_id": material_id, "rate": 18.0},
        headers=admin_headers,
    )

    yield point_id, material_id

    with SessionLocal() as db:
        db.query(MaterialRate).filter(MaterialRate.collection_point_id == point_id).delete()
        db.query(CollectionPointMaterial).filter(CollectionPointMaterial.collection_point_id == point_id).delete()
        db.query(CollectionPoint).filter(CollectionPoint.id == point_id).delete()
        db.query(Material).filter(Material.id == material_id).delete()
        db.commit()


@pytest.fixture
def inactive_point(admin_headers):
    point_resp = client.post(
        "/api/v1/collection-points",
        json={"name": "Public Inactive Branch", "address": "2 Public Rd", "county": "Nairobi"},
        headers=admin_headers,
    )
    point_id = point_resp.json()["id"]
    client.patch(f"/api/v1/collection-points/{point_id}", json={"is_active": False}, headers=admin_headers)

    yield point_id

    with SessionLocal() as db:
        db.query(CollectionPoint).filter(CollectionPoint.id == point_id).delete()
        db.commit()


def test_public_endpoints_need_no_auth(active_point_with_material):
    point_id, _ = active_point_with_material
    response = client.get("/api/v1/public/collection-points")
    assert response.status_code == 200
    response = client.get(f"/api/v1/public/collection-points/{point_id}/materials")
    assert response.status_code == 200


def test_public_list_includes_active_branch(active_point_with_material):
    point_id, _ = active_point_with_material
    response = client.get("/api/v1/public/collection-points")
    ids = [p["id"] for p in response.json()]
    assert point_id in ids


def test_public_list_excludes_inactive_branch(inactive_point):
    response = client.get("/api/v1/public/collection-points")
    ids = [p["id"] for p in response.json()]
    assert inactive_point not in ids


def test_public_materials_for_inactive_branch_is_404(inactive_point):
    response = client.get(f"/api/v1/public/collection-points/{inactive_point}/materials")
    assert response.status_code == 404


def test_public_materials_show_rate(active_point_with_material):
    point_id, material_id = active_point_with_material
    response = client.get(f"/api/v1/public/collection-points/{point_id}/materials")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["material"]["id"] == material_id
    assert body[0]["current_rate"]["rate"] == 18.0
