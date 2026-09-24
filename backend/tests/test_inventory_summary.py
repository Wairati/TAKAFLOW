"""§19 / Phase 9: the admin/staff read view over the Phase 5 ledger-backed
balances, and the "today's collections" date filter. Against the real
database."""

import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.collection_point import CollectionPoint
from app.models.collection_transaction import CollectionTransaction
from app.models.inventory import InventoryLedger, InventorySummary
from app.models.material import CollectionPointMaterial, Material, MaterialRate
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole

client = TestClient(app)

ADMIN_PASSWORD = "admin-test-password-123"
STAFF_PASSWORD = "staff-test-password-123"


def _login(email: str, password: str) -> dict:
    response = client.post("/api/v1/auth/login", json={"identifier": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin_headers():
    with SessionLocal() as db:
        user = User(
            email="inv.admin@example.com", hashed_password=hash_password(ADMIN_PASSWORD),
            full_name="Inv Admin", role=UserRole.ADMIN,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    yield _login("inv.admin@example.com", ADMIN_PASSWORD)

    with SessionLocal() as db:
        db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


@pytest.fixture
def point_with_material(admin_headers):
    point_resp = client.post(
        "/api/v1/collection-points",
        json={"name": "Inv Test Branch", "address": "1 Test Rd", "county": "Nairobi"},
        headers=admin_headers,
    )
    point_id = point_resp.json()["id"]

    material_resp = client.post(
        "/api/v1/materials", json={"name": "Inv Test Material", "unit": "kg"}, headers=admin_headers
    )
    material_id = material_resp.json()["id"]

    client.post(
        f"/api/v1/collection-points/{point_id}/materials",
        json={"material_id": material_id, "rate": 20.0},
        headers=admin_headers,
    )

    yield point_id, material_id

    with SessionLocal() as db:
        db.query(InventoryLedger).filter(InventoryLedger.collection_point_id == point_id).delete()
        db.query(InventorySummary).filter(InventorySummary.collection_point_id == point_id).delete()
        db.query(CollectionTransaction).filter(CollectionTransaction.collection_point_id == point_id).delete()
        db.query(MaterialRate).filter(MaterialRate.collection_point_id == point_id).delete()
        db.query(CollectionPointMaterial).filter(CollectionPointMaterial.collection_point_id == point_id).delete()
        db.query(CollectionPoint).filter(CollectionPoint.id == point_id).delete()
        db.query(Material).filter(Material.id == material_id).delete()
        db.commit()


@pytest.fixture
def staff_headers(point_with_material):
    point_id, _ = point_with_material
    with SessionLocal() as db:
        user = User(
            email="inv.staff@example.com", hashed_password=hash_password(STAFF_PASSWORD),
            full_name="Inv Staff", role=UserRole.COLLECTION_POINT_STAFF, collection_point_id=point_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    yield _login("inv.staff@example.com", STAFF_PASSWORD)

    with SessionLocal() as db:
        db.query(CollectionTransaction).filter(CollectionTransaction.recorded_by_user_id == user_id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


def test_inventory_summary_reflects_recorded_collections(staff_headers, admin_headers, point_with_material):
    point_id, material_id = point_with_material
    client.post(
        "/api/v1/collection-transactions",
        json={"client_transaction_uuid": str(uuid.uuid4()), "material_id": material_id, "quantity": 8},
        headers=staff_headers,
    )

    response = client.get(
        "/api/v1/inventory/summary", params={"collection_point_id": point_id}, headers=admin_headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 1
    assert body[0]["material_name"] == "Inv Test Material"
    assert body[0]["quantity_on_hand"] == 8.0


def test_staff_cannot_view_other_points_inventory(staff_headers, admin_headers):
    other_point_resp = client.post(
        "/api/v1/collection-points",
        json={"name": "Inv Other Branch", "address": "2 Test Rd", "county": "Nairobi"},
        headers=admin_headers,
    )
    other_point_id = other_point_resp.json()["id"]

    response = client.get(
        "/api/v1/inventory/summary", params={"collection_point_id": other_point_id}, headers=staff_headers
    )
    assert response.status_code == 403

    with SessionLocal() as db:
        db.query(CollectionPoint).filter(CollectionPoint.id == other_point_id).delete()
        db.commit()


def test_on_date_filter_isolates_todays_collections(staff_headers, admin_headers, point_with_material):
    point_id, material_id = point_with_material
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    # One transaction "today" (default occurred_at), one backdated to yesterday.
    client.post(
        "/api/v1/collection-transactions",
        json={"client_transaction_uuid": str(uuid.uuid4()), "material_id": material_id, "quantity": 1},
        headers=staff_headers,
    )
    client.post(
        "/api/v1/collection-transactions",
        json={
            "client_transaction_uuid": str(uuid.uuid4()),
            "material_id": material_id,
            "quantity": 2,
            "occurred_at": f"{yesterday}T09:00:00Z",
        },
        headers=staff_headers,
    )

    today_response = client.get(
        "/api/v1/collection-transactions",
        params={"collection_point_id": point_id, "on_date": date.today().isoformat()},
        headers=admin_headers,
    )
    assert today_response.status_code == 200
    assert len(today_response.json()) == 1
    assert today_response.json()[0]["quantity"] == 1.0

    yesterday_response = client.get(
        "/api/v1/collection-transactions",
        params={"collection_point_id": point_id, "on_date": yesterday},
        headers=admin_headers,
    )
    assert len(yesterday_response.json()) == 1
    assert yesterday_response.json()[0]["quantity"] == 2.0
