"""Inventory summary reads and the reports aggregation that reads collection,
"sold" (paid buyer orders), and payment activity. Against the real database,
same fixture pattern as the other branch-scoped test modules.

"Sold" here comes from buyer-order payments (recording a payment both
approves the order and reduces the branch's stock) rather than any standalone
sale-recording endpoint — there isn't one."""

import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.buyer_order import BuyerOrder, BuyerOrderPayment
from app.models.collection_point import CollectionPoint
from app.models.collection_transaction import CollectionTransaction
from app.models.inventory import InventoryLedger, InventorySummary
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
        "/api/v1/materials",
        json={"name": "Rpt Test Material", "unit": "kg", "selling_rate": 100.0},
        headers=admin_headers,
    )
    material_id = material_resp.json()["id"]

    client.post(
        f"/api/v1/collection-points/{point_id}/materials",
        json={"material_id": material_id, "rate": 20.0},
        headers=admin_headers,
    )

    yield point_id, material_id

    with SessionLocal() as db:
        db.query(BuyerOrderPayment).filter(
            BuyerOrderPayment.buyer_order_id.in_(
                db.query(BuyerOrder.id).filter(BuyerOrder.collection_point_id == point_id)
            )
        ).delete(synchronize_session=False)
        db.query(BuyerOrder).filter(BuyerOrder.collection_point_id == point_id).delete()
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
        # Must go before the user delete below: buyer_order.created_by_user_id
        # and audit_log.user_id both reference this user with no cascade.
        db.query(BuyerOrderPayment).filter(
            BuyerOrderPayment.buyer_order_id.in_(
                db.query(BuyerOrder.id).filter(BuyerOrder.created_by_user_id == user_id)
            )
        ).delete(synchronize_session=False)
        db.query(BuyerOrder).filter(BuyerOrder.created_by_user_id == user_id).delete()
        db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
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


def _create_and_pay_order(headers: dict, material_id: int, quantity: float) -> None:
    order_resp = client.post(
        "/api/v1/buyer-orders",
        json={"buyer_name": "Acme Recyclers", "material_id": material_id, "quantity_requested": quantity},
        headers=headers,
    )
    assert order_resp.status_code == 201, order_resp.text
    order_id = order_resp.json()["id"]

    pay_resp = client.post(
        f"/api/v1/buyer-orders/{order_id}/payments", json={"method": "cash"}, headers=headers
    )
    assert pay_resp.status_code == 201, pay_resp.text


# ---- Reports summary ----


def test_reports_summary_aggregates_collections_sold_orders_and_payments(staff_headers, point_with_material):
    point_id, material_id = point_with_material
    tx_id = _record_collection(staff_headers, material_id, 10)

    payment_response = client.post(
        f"/api/v1/collection-transactions/{tx_id}/payments",
        json={"method": "cash", "amount": 150},
        headers=staff_headers,
    )
    assert payment_response.status_code == 201, payment_response.text

    _create_and_pay_order(staff_headers, material_id, 4)

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


def test_reports_admin_omitting_branch_means_all_branches(admin_headers):
    today = date.today().isoformat()
    response = client.get(
        "/api/v1/reports/summary", params={"from_date": today, "to_date": today}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["collection_point_id"] is None


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


# ---- Timeseries ----


def test_timeseries_has_one_point_per_day_with_activity_on_the_right_day(staff_headers, point_with_material):
    _, material_id = point_with_material
    _record_collection(staff_headers, material_id, 10)

    today = date.today().isoformat()
    response = client.get(
        "/api/v1/reports/timeseries", params={"from_date": today, "to_date": today}, headers=staff_headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["points"]) == 1
    assert body["points"][0]["day"] == today
    assert body["points"][0]["collected_quantity"] == 10.0


def test_timeseries_fills_zero_for_days_with_no_activity(staff_headers, point_with_material):
    from datetime import timedelta

    today = date.today()
    three_days_ago = (today - timedelta(days=3)).isoformat()
    response = client.get(
        "/api/v1/reports/timeseries",
        params={"from_date": three_days_ago, "to_date": today.isoformat()},
        headers=staff_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["points"]) == 4
    assert all(p["collected_quantity"] == 0.0 for p in body["points"])


def test_timeseries_requires_role_scoping(staff_headers, admin_headers):
    other_point_resp = client.post(
        "/api/v1/collection-points",
        json={"name": "Ts Other Branch", "address": "5 Test Rd", "county": "Nairobi"},
        headers=admin_headers,
    )
    other_point_id = other_point_resp.json()["id"]
    today = date.today().isoformat()

    response = client.get(
        "/api/v1/reports/timeseries",
        params={"from_date": today, "to_date": today, "collection_point_id": other_point_id},
        headers=staff_headers,
    )
    assert response.status_code == 403

    with SessionLocal() as db:
        db.query(CollectionPoint).filter(CollectionPoint.id == other_point_id).delete()
        db.commit()


# ---- By-branch (admin only, company-wide comparison) ----


def test_by_branch_requires_admin(staff_headers):
    today = date.today().isoformat()
    response = client.get(
        "/api/v1/reports/by-branch", params={"from_date": today, "to_date": today}, headers=staff_headers
    )
    assert response.status_code == 403


def test_by_branch_includes_active_branches(admin_headers, staff_headers, point_with_material):
    point_id, material_id = point_with_material
    _record_collection(staff_headers, material_id, 7)

    today = date.today().isoformat()
    response = client.get(
        "/api/v1/reports/by-branch", params={"from_date": today, "to_date": today}, headers=admin_headers
    )
    assert response.status_code == 200, response.text
    branches = {b["collection_point_id"]: b for b in response.json()["branches"]}
    assert point_id in branches
    assert branches[point_id]["collected_quantity"] == 7.0
