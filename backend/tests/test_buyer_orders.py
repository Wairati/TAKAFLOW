"""Buyer orders: creation (tied to one branch), payment (recording a payment
is itself the approval, no separate admin verification step, and decrements
that branch's inventory in the same step), and cancellation. Against the
real database."""

import uuid

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
            email="bo.admin@example.com", hashed_password=hash_password(ADMIN_PASSWORD),
            full_name="Bo Admin", role=UserRole.ADMIN,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    yield _login("bo.admin@example.com", ADMIN_PASSWORD)

    with SessionLocal() as db:
        db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


@pytest.fixture
def material(admin_headers):
    response = client.post(
        "/api/v1/materials",
        json={"name": "Bo Test Aluminium", "unit": "kg", "selling_rate": 250.0},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    material_id = response.json()["id"]

    yield material_id

    with SessionLocal() as db:
        db.query(Material).filter(Material.id == material_id).delete()
        db.commit()


@pytest.fixture
def branch_with_staff(admin_headers, material):
    point_resp = client.post(
        "/api/v1/collection-points",
        json={"name": "Bo Branch A", "address": "1 Test Rd", "county": "Nairobi"},
        headers=admin_headers,
    )
    point_id = point_resp.json()["id"]

    client.post(
        f"/api/v1/collection-points/{point_id}/materials",
        json={"material_id": material, "rate": 15.0},
        headers=admin_headers,
    )

    employee_number = "930001"
    with SessionLocal() as db:
        user = User(
            email="bo.staff.a@example.com", hashed_password=hash_password(STAFF_PASSWORD),
            full_name="Bo Staff A", role=UserRole.COLLECTION_POINT_STAFF,
            employee_number=employee_number, collection_point_id=point_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        staff_id = user.id
        staff_headers = _login(employee_number, STAFF_PASSWORD)

    yield point_id, staff_headers

    with SessionLocal() as db:
        db.query(InventoryLedger).filter(InventoryLedger.collection_point_id == point_id).delete()
        db.query(InventorySummary).filter(InventorySummary.collection_point_id == point_id).delete()
        db.query(CollectionTransaction).filter(CollectionTransaction.collection_point_id == point_id).delete()
        db.query(MaterialRate).filter(MaterialRate.collection_point_id == point_id).delete()
        db.query(CollectionPointMaterial).filter(CollectionPointMaterial.collection_point_id == point_id).delete()
        db.commit()
        db.query(RefreshToken).filter(RefreshToken.user_id == staff_id).delete()
        db.query(User).filter(User.id == staff_id).delete()
        db.query(CollectionPoint).filter(CollectionPoint.id == point_id).delete()
        db.query(Material).filter(Material.id == material).delete()
        db.commit()


def _record_collection(headers: dict, material_id: int, quantity: float) -> None:
    response = client.post(
        "/api/v1/collection-transactions",
        json={"client_transaction_uuid": str(uuid.uuid4()), "material_id": material_id, "quantity": quantity},
        headers=headers,
    )
    assert response.status_code == 201, response.text


def _create_order(
    headers: dict, material_id: int, quantity: float, *, collection_point_id: int | None = None, buyer_name: str = "Acme Buyers"
) -> dict:
    payload = {"buyer_name": buyer_name, "buyer_phone": "0722334455", "material_id": material_id, "quantity_requested": quantity}
    if collection_point_id is not None:
        payload["collection_point_id"] = collection_point_id
    response = client.post("/api/v1/buyer-orders", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _cleanup_order(order_id: int) -> None:
    with SessionLocal() as db:
        db.query(BuyerOrderPayment).filter(BuyerOrderPayment.buyer_order_id == order_id).delete()
        db.query(AuditLog).filter(AuditLog.entity_type == "buyer_order", AuditLog.entity_id == order_id).delete()
        db.query(BuyerOrder).filter(BuyerOrder.id == order_id).delete()
        db.commit()


# ---- Creating and listing orders -------------------------------------------


def test_staff_can_create_order(branch_with_staff, material):
    point_id, staff_headers = branch_with_staff
    order = _create_order(staff_headers, material, 10)
    assert order["status"] == "open"
    assert order["collection_point_id"] == point_id
    _cleanup_order(order["id"])


def test_admin_can_create_order_for_a_chosen_branch(branch_with_staff, admin_headers, material):
    point_id, _ = branch_with_staff
    order = _create_order(admin_headers, material, 10, collection_point_id=point_id)
    assert order["status"] == "open"
    assert order["collection_point_id"] == point_id
    _cleanup_order(order["id"])


def test_admin_must_choose_a_branch(admin_headers, material):
    response = client.post(
        "/api/v1/buyer-orders",
        json={"buyer_name": "Acme Buyers", "material_id": material, "quantity_requested": 10},
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_list_and_get_order(branch_with_staff, material):
    _, staff_headers = branch_with_staff
    order = _create_order(staff_headers, material, 10)

    listed = client.get("/api/v1/buyer-orders", headers=staff_headers)
    assert listed.status_code == 200
    assert any(o["id"] == order["id"] for o in listed.json())

    fetched = client.get(f"/api/v1/buyer-orders/{order['id']}", headers=staff_headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == order["id"]

    _cleanup_order(order["id"])


# ---- Payment: recording it is itself the approval, and moves stock ----------


def test_staff_recording_payment_moves_order_straight_to_paid_and_reduces_stock(branch_with_staff, material):
    point_id, staff_headers = branch_with_staff
    _record_collection(staff_headers, material, 10)
    order = _create_order(staff_headers, material, 6)

    pay_resp = client.post(
        f"/api/v1/buyer-orders/{order['id']}/payments",
        json={"method": "cash"},
        headers=staff_headers,
    )
    assert pay_resp.status_code == 201, pay_resp.text
    # 6 kg at the material's 250.0/kg selling rate, computed server-side.
    assert pay_resp.json()["amount"] == 1500.0

    now_paid = client.get(f"/api/v1/buyer-orders/{order['id']}", headers=staff_headers).json()
    assert now_paid["status"] == "paid"

    summary = client.get(
        "/api/v1/inventory/summary", params={"collection_point_id": point_id}, headers=staff_headers
    ).json()
    assert summary[0]["quantity_on_hand"] == 4.0

    _cleanup_order(order["id"])


def test_admin_recording_payment_moves_order_straight_to_paid(branch_with_staff, admin_headers, material):
    point_id, staff_headers = branch_with_staff
    _record_collection(staff_headers, material, 10)
    order = _create_order(admin_headers, material, 10, collection_point_id=point_id)

    pay_resp = client.post(
        f"/api/v1/buyer-orders/{order['id']}/payments",
        json={"method": "cash"},
        headers=admin_headers,
    )
    assert pay_resp.status_code == 201, pay_resp.text

    now_paid = client.get(f"/api/v1/buyer-orders/{order['id']}", headers=admin_headers).json()
    assert now_paid["status"] == "paid"

    _cleanup_order(order["id"])


def test_payment_rejected_when_branch_has_insufficient_stock(branch_with_staff, material):
    _, staff_headers = branch_with_staff
    order = _create_order(staff_headers, material, 10)  # no collection recorded — 0 on hand

    response = client.post(
        f"/api/v1/buyer-orders/{order['id']}/payments", json={"method": "cash"}, headers=staff_headers
    )
    assert response.status_code == 422

    still_open = client.get(f"/api/v1/buyer-orders/{order['id']}", headers=staff_headers).json()
    assert still_open["status"] == "open"

    # The rejected payment must not have been left behind either.
    payments = client.get(f"/api/v1/buyer-orders/{order['id']}/payments", headers=staff_headers).json()
    assert payments == []

    _cleanup_order(order["id"])


def test_cannot_pay_an_already_paid_order(branch_with_staff, material):
    _, staff_headers = branch_with_staff
    _record_collection(staff_headers, material, 20)
    order = _create_order(staff_headers, material, 10)
    client.post(f"/api/v1/buyer-orders/{order['id']}/payments", json={"method": "cash"}, headers=staff_headers)

    response = client.post(
        f"/api/v1/buyer-orders/{order['id']}/payments", json={"method": "cash"}, headers=staff_headers
    )
    assert response.status_code == 409

    _cleanup_order(order["id"])


def test_mpesa_payment_requires_reference(branch_with_staff, material):
    _, staff_headers = branch_with_staff
    _record_collection(staff_headers, material, 10)
    order = _create_order(staff_headers, material, 10)
    response = client.post(
        f"/api/v1/buyer-orders/{order['id']}/payments", json={"method": "mpesa"}, headers=staff_headers
    )
    assert response.status_code == 422
    _cleanup_order(order["id"])


def test_payment_rejected_when_material_has_no_selling_rate(branch_with_staff, material):
    _, staff_headers = branch_with_staff
    _record_collection(staff_headers, material, 10)
    order = _create_order(staff_headers, material, 10)

    with SessionLocal() as db:
        row = db.get(Material, material)
        row.selling_rate = None
        db.commit()

    response = client.post(
        f"/api/v1/buyer-orders/{order['id']}/payments", json={"method": "cash"}, headers=staff_headers
    )
    assert response.status_code == 409

    _cleanup_order(order["id"])


def test_list_payments(branch_with_staff, material):
    _, staff_headers = branch_with_staff
    _record_collection(staff_headers, material, 10)
    order = _create_order(staff_headers, material, 10)
    client.post(f"/api/v1/buyer-orders/{order['id']}/payments", json={"method": "cash"}, headers=staff_headers)

    response = client.get(f"/api/v1/buyer-orders/{order['id']}/payments", headers=staff_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    _cleanup_order(order["id"])


# ---- Cancellation -----------------------------------------------------------


def test_admin_can_cancel_open_order(branch_with_staff, admin_headers, material):
    _, staff_headers = branch_with_staff
    order = _create_order(staff_headers, material, 10)

    response = client.post(f"/api/v1/buyer-orders/{order['id']}/cancel", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    _cleanup_order(order["id"])


def test_staff_cannot_cancel_order(branch_with_staff, material):
    _, staff_headers = branch_with_staff
    order = _create_order(staff_headers, material, 10)

    response = client.post(f"/api/v1/buyer-orders/{order['id']}/cancel", headers=staff_headers)
    assert response.status_code == 403

    _cleanup_order(order["id"])


def test_cannot_cancel_order_once_paid(branch_with_staff, admin_headers, material):
    _, staff_headers = branch_with_staff
    _record_collection(staff_headers, material, 10)
    order = _create_order(staff_headers, material, 5)
    client.post(f"/api/v1/buyer-orders/{order['id']}/payments", json={"method": "cash"}, headers=staff_headers)

    response = client.post(f"/api/v1/buyer-orders/{order['id']}/cancel", headers=admin_headers)
    assert response.status_code == 409

    _cleanup_order(order["id"])
