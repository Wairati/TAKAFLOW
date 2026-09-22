"""§10: the sync endpoint is the offline outbox's server side — a batch is
processed item-by-item, one failure never poisons the rest, and replaying
an already-synced item is idempotent. Against the real database."""

import uuid
from decimal import Decimal

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
from app.services import inventory_service

client = TestClient(app)

ADMIN_PASSWORD = "admin-test-password-123"
STAFF_PASSWORD = "staff-test-password-123"


def _login(email: str, password: str) -> dict:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin_headers():
    with SessionLocal() as db:
        user = User(
            email="sync.admin@example.com", hashed_password=hash_password(ADMIN_PASSWORD),
            full_name="Sync Admin", role=UserRole.ADMIN,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    yield _login("sync.admin@example.com", ADMIN_PASSWORD)

    with SessionLocal() as db:
        db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


@pytest.fixture
def point_with_material(admin_headers):
    point_resp = client.post(
        "/api/v1/collection-points",
        json={"name": "Sync Test Branch", "address": "1 Test Rd", "county": "Nairobi"},
        headers=admin_headers,
    )
    point_id = point_resp.json()["id"]

    material_resp = client.post(
        "/api/v1/materials", json={"name": "Sync Test Material", "unit": "kg"}, headers=admin_headers
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
            email="sync.staff@example.com", hashed_password=hash_password(STAFF_PASSWORD),
            full_name="Sync Staff", role=UserRole.COLLECTION_POINT_STAFF, collection_point_id=point_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    yield _login("sync.staff@example.com", STAFF_PASSWORD)

    with SessionLocal() as db:
        db.query(CollectionTransaction).filter(CollectionTransaction.recorded_by_user_id == user_id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


def test_admin_cannot_sync(admin_headers):
    response = client.post("/api/v1/sync/collection-transactions", json={"items": []}, headers=admin_headers)
    assert response.status_code == 403


def test_batch_syncs_multiple_items(staff_headers, point_with_material):
    point_id, material_id = point_with_material
    items = [
        {"client_transaction_uuid": str(uuid.uuid4()), "material_id": material_id, "quantity": q}
        for q in (2, 3, 5)
    ]
    response = client.post(
        "/api/v1/sync/collection-transactions", json={"items": items}, headers=staff_headers
    )
    assert response.status_code == 200, response.text
    results = response.json()["results"]
    assert all(r["status"] == "synced" for r in results)

    with SessionLocal() as db:
        balance = inventory_service.get_balance(db, point_id, material_id)
        assert balance.quantity_on_hand == Decimal("10.00")


def test_batch_one_bad_item_does_not_affect_others(staff_headers, point_with_material):
    point_id, material_id = point_with_material

    with SessionLocal() as db:
        unaccepted = Material(name="Sync Unaccepted Material", unit="kg")
        db.add(unaccepted)
        db.commit()
        db.refresh(unaccepted)
        unaccepted_id = unaccepted.id

    items = [
        {"client_transaction_uuid": str(uuid.uuid4()), "material_id": material_id, "quantity": 4},
        {"client_transaction_uuid": str(uuid.uuid4()), "material_id": unaccepted_id, "quantity": 100},
        {"client_transaction_uuid": str(uuid.uuid4()), "material_id": material_id, "quantity": 6},
    ]
    response = client.post(
        "/api/v1/sync/collection-transactions", json={"items": items}, headers=staff_headers
    )
    assert response.status_code == 200, response.text
    results = response.json()["results"]
    assert results[0]["status"] == "synced"
    assert results[1]["status"] == "conflict"
    assert results[2]["status"] == "synced"  # not poisoned by item 2's failure

    with SessionLocal() as db:
        balance = inventory_service.get_balance(db, point_id, material_id)
        assert balance.quantity_on_hand == Decimal("10.00")  # 4 + 6, not affected by the conflict
        db.query(Material).filter(Material.id == unaccepted_id).delete()
        db.commit()


def test_batch_replay_is_idempotent(staff_headers, point_with_material):
    point_id, material_id = point_with_material
    items = [{"client_transaction_uuid": str(uuid.uuid4()), "material_id": material_id, "quantity": 7}]

    first = client.post("/api/v1/sync/collection-transactions", json={"items": items}, headers=staff_headers)
    assert first.json()["results"][0]["status"] == "synced"

    # Simulates a dropped connection after the server applied it but before
    # the client saw the response - the client retries the same batch.
    second = client.post("/api/v1/sync/collection-transactions", json={"items": items}, headers=staff_headers)
    assert second.json()["results"][0]["status"] == "synced"
    assert (
        second.json()["results"][0]["collection_transaction"]["id"]
        == first.json()["results"][0]["collection_transaction"]["id"]
    )

    with SessionLocal() as db:
        balance = inventory_service.get_balance(db, point_id, material_id)
        assert balance.quantity_on_hand == Decimal("7.00")  # not 14
