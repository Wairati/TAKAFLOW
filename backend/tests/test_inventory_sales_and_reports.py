"""Inventory outflow (recording a sale) and the reports aggregation that
reads both directions of the ledger plus payments. Against the real database,
same fixture pattern as test_inventory_summary.py."""

import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.collection_point import CollectionPoint
from app.models.collection_transaction import CollectionTransaction
from app.models.inventory import InventoryLedger, InventorySummary
from app.models.inventory_sale import InventorySale
from app.models.material import CollectionPointMaterial, Material, MaterialRate
from app.models.payment import Payment
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
            email="rpt.admin@example.com", hashed_password=hash_password(ADMIN_PASSWORD),
            full_name="Rpt Admin", role=UserRole.ADMIN,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    yield _login("rpt.admin@example.com", ADMIN_PASSWORD)

    with SessionLocal() as db:
        db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


@pytest.fixture
def point_with_material(admin_headers):
    point_resp = client.post(
        "/api/v1/collection-points",
        json={"name": "Rpt Test Branch", "address": "1 Test Rd", "county": "Nairobi"},
        headers=admin_headers,
    )
    point_id = point_resp.json()["id"]

    material_resp = client.post(
        "/api/v1/materials", json={"name": "Rpt Test Material", "unit": "kg"}, headers=admin_headers
    )
    material_id = material_resp.json()["id"]

    client.post(
        f"/api/v1/collection-points/{point_id}/materials",
        json={"material_id": material_id, "rate": 20.0},
        headers=admin_headers,
    )

    yield point_id, material_id

    with SessionLocal() as db:
        db.query(InventorySale).filter(InventorySale.collection_point_id == point_id).delete()
        db.query(InventoryLedger).filter(InventoryLedger.collection_point_id == point_id).delete()
        db.query(InventorySummary).filter(InventorySummary.collection_point_id == point_id).delete()
        db.query(Payment).filter(
            Payment.collection_transaction_id.in_(
                db.query(CollectionTransaction.id).filter(CollectionTransaction.collection_point_id == point_id)
            )
        ).delete(synchronize_session=False)
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
            email="rpt.staff@example.com", hashed_password=hash_password(STAFF_PASSWORD),
            full_name="Rpt Staff", role=UserRole.COLLECTION_POINT_STAFF, collection_point_id=point_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    yield _login("rpt.staff@example.com", STAFF_PASSWORD)

    with SessionLocal() as db:
        db.query(InventorySale).filter(InventorySale.recorded_by_user_id == user_id).delete()
        db.query(Payment).filter(
            Payment.collection_transaction_id.in_(
                db.query(CollectionTransaction.id).filter(CollectionTransaction.recorded_by_user_id == user_id)
            )
        ).delete(synchronize_session=False)
        db.query(CollectionTransaction).filter(CollectionTransaction.recorded_by_user_id == user_id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


def _record_collection(headers: dict, material_id: int, quantity: float) -> int:
    response = client.post(
        "/api/v1/collection-transactions",
        json={"client_transaction_uuid": str(uuid.uuid4()), "material_id": material_id, "quantity": quantity},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


# ---- Recording a sale (inventory outflow) ----


def test_record_sale_reduces_inventory(staff_headers, admin_headers, point_with_material):
    point_id, material_id = point_with_material
    _record_collection(staff_headers, material_id, 10)

    sale_response = client.post(
        "/api/v1/inventory/sales",
        json={"material_id": material_id, "quantity": 6, "sold_to": "Acme Recyclers"},
        headers=staff_headers,
    )
    assert sale_response.status_code == 201, sale_response.text
    assert sale_response.json()["sold_to"] == "Acme Recyclers"

    summary = client.get(
        "/api/v1/inventory/summary", params={"collection_point_id": point_id}, headers=admin_headers
    ).json()
    assert summary[0]["quantity_on_hand"] == 4.0


def test_record_sale_rejects_insufficient_stock(staff_headers, point_with_material):
    _, material_id = point_with_material
    _record_collection(staff_headers, material_id, 5)

    response = client.post(
        "/api/v1/inventory/sales",
        json={"material_id": material_id, "quantity": 999},
        headers=staff_headers,
    )
    assert response.status_code == 422


def test_record_sale_requires_staff_role(admin_headers, point_with_material):
    _, material_id = point_with_material
    response = client.post(
        "/api/v1/inventory/sales",
        json={"material_id": material_id, "quantity": 1},
        headers=admin_headers,
    )
    assert response.status_code == 403


def test_staff_cannot_list_other_branch_sales(staff_headers, admin_headers):
    other_point_resp = client.post(
        "/api/v1/collection-points",
        json={"name": "Rpt Other Branch", "address": "2 Test Rd", "county": "Nairobi"},
        headers=admin_headers,
    )
    other_point_id = other_point_resp.json()["id"]

    response = client.get(
        "/api/v1/inventory/sales", params={"collection_point_id": other_point_id}, headers=staff_headers
    )
    assert response.status_code == 403

    with SessionLocal() as db:
        db.query(CollectionPoint).filter(CollectionPoint.id == other_point_id).delete()
        db.commit()


# ---- Reports summary ----


def test_reports_summary_aggregates_collections_sales_and_payments(staff_headers, point_with_material):
    point_id, material_id = point_with_material
    tx_id = _record_collection(staff_headers, material_id, 10)

    payment_response = client.post(
        f"/api/v1/collection-transactions/{tx_id}/payments",
        json={"method": "cash", "amount": 150},
        headers=staff_headers,
    )
    assert payment_response.status_code == 201, payment_response.text

    client.post(
        "/api/v1/inventory/sales",
        json={"material_id": material_id, "quantity": 4, "sold_to": "Acme Recyclers"},
        headers=staff_headers,
    )

    today = date.today().isoformat()
    response = client.get(
        "/api/v1/reports/summary",
        params={"from_date": today, "to_date": today},
        headers=staff_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["total_collected_quantity"] == 10.0
    assert body["collected_by_material"] == [
        {"material_id": material_id, "material_name": "Rpt Test Material", "quantity": 10.0}
    ]
    assert body["total_sold_quantity"] == 4.0
    assert body["sold_by_material"] == [
        {"material_id": material_id, "material_name": "Rpt Test Material", "quantity": 4.0}
    ]
    assert body["total_payments_amount"] == 150.0


def test_reports_admin_requires_collection_point_id(admin_headers):
    today = date.today().isoformat()
    response = client.get(
        "/api/v1/reports/summary", params={"from_date": today, "to_date": today}, headers=admin_headers
    )
    assert response.status_code == 422


def test_reports_staff_cannot_specify_other_branch(staff_headers, admin_headers):
    other_point_resp = client.post(
        "/api/v1/collection-points",
        json={"name": "Rpt Other Branch 2", "address": "3 Test Rd", "county": "Nairobi"},
        headers=admin_headers,
    )
    other_point_id = other_point_resp.json()["id"]
    today = date.today().isoformat()

    response = client.get(
        "/api/v1/reports/summary",
        params={"from_date": today, "to_date": today, "collection_point_id": other_point_id},
        headers=staff_headers,
    )
    assert response.status_code == 403

    with SessionLocal() as db:
        db.query(CollectionPoint).filter(CollectionPoint.id == other_point_id).delete()
        db.commit()


def test_reports_rejects_inverted_date_range(staff_headers):
    response = client.get(
        "/api/v1/reports/summary",
        params={"from_date": "2026-01-10", "to_date": "2026-01-01"},
        headers=staff_headers,
    )
    assert response.status_code == 422
