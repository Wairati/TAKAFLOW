"""§19 / §25 item 2: manual payment recording — method + reference, no live
M-Pesa disbursement. All against the real database."""

import uuid

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
            email="pay.admin@example.com", hashed_password=hash_password(ADMIN_PASSWORD),
            full_name="Pay Admin", role=UserRole.ADMIN,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    yield _login("pay.admin@example.com", ADMIN_PASSWORD)

    with SessionLocal() as db:
        db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


@pytest.fixture
def point_with_material(admin_headers):
    point_resp = client.post(
        "/api/v1/collection-points",
        json={"name": "Pay Test Branch", "address": "1 Test Rd", "county": "Nairobi"},
        headers=admin_headers,
    )
    point_id = point_resp.json()["id"]

    material_resp = client.post(
        "/api/v1/materials", json={"name": "Pay Test Material", "unit": "kg"}, headers=admin_headers
    )
    material_id = material_resp.json()["id"]

    client.post(
        f"/api/v1/collection-points/{point_id}/materials",
        json={"material_id": material_id, "rate": 20.0},
        headers=admin_headers,
    )

    yield point_id, material_id

    with SessionLocal() as db:
        transaction_ids = [
            t.id for t in db.query(CollectionTransaction).filter(
                CollectionTransaction.collection_point_id == point_id
            ).all()
        ]
        if transaction_ids:
            db.query(Payment).filter(Payment.collection_transaction_id.in_(transaction_ids)).delete(
                synchronize_session=False
            )
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
            email="pay.staff@example.com", hashed_password=hash_password(STAFF_PASSWORD),
            full_name="Pay Staff", role=UserRole.COLLECTION_POINT_STAFF, collection_point_id=point_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    yield _login("pay.staff@example.com", STAFF_PASSWORD)

    with SessionLocal() as db:
        # Same ordering lesson as Phase 6, one level deeper: this fixture
        # tears down before point_with_material's (reverse of setup order),
        # so anything FK-referencing this user's transactions — now including
        # Payment rows, which reference the transaction which references the
        # user — must be cleared first, or deleting either violates a FK.
        transaction_ids = [
            t.id for t in db.query(CollectionTransaction).filter(
                CollectionTransaction.recorded_by_user_id == user_id
            ).all()
        ]
        if transaction_ids:
            db.query(Payment).filter(Payment.collection_transaction_id.in_(transaction_ids)).delete(
                synchronize_session=False
            )
        db.query(CollectionTransaction).filter(CollectionTransaction.recorded_by_user_id == user_id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


@pytest.fixture
def transaction_id(staff_headers, point_with_material):
    _, material_id = point_with_material
    response = client.post(
        "/api/v1/collection-transactions",
        json={"client_transaction_uuid": str(uuid.uuid4()), "material_id": material_id, "quantity": 5},
        headers=staff_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_admin_cannot_record_payment(admin_headers, transaction_id):
    response = client.post(
        f"/api/v1/collection-transactions/{transaction_id}/payments",
        json={"method": "cash", "amount": 100},
        headers=admin_headers,
    )
    assert response.status_code == 403


def test_cash_payment_needs_no_reference(staff_headers, transaction_id):
    response = client.post(
        f"/api/v1/collection-transactions/{transaction_id}/payments",
        json={"method": "cash", "amount": 100},
        headers=staff_headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["reference_number"] is None


def test_mpesa_payment_requires_reference(staff_headers, transaction_id):
    response = client.post(
        f"/api/v1/collection-transactions/{transaction_id}/payments",
        json={"method": "mpesa", "amount": 100},
        headers=staff_headers,
    )
    assert response.status_code == 422


def test_mpesa_payment_with_reference_succeeds(staff_headers, transaction_id):
    response = client.post(
        f"/api/v1/collection-transactions/{transaction_id}/payments",
        json={"method": "mpesa", "amount": 100, "reference_number": "QGH7XJ2K9P"},
        headers=staff_headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["reference_number"] == "QGH7XJ2K9P"


def test_multiple_payments_allowed_on_one_transaction(staff_headers, transaction_id):
    client.post(
        f"/api/v1/collection-transactions/{transaction_id}/payments",
        json={"method": "cash", "amount": 60},
        headers=staff_headers,
    )
    client.post(
        f"/api/v1/collection-transactions/{transaction_id}/payments",
        json={"method": "mpesa", "amount": 40, "reference_number": "ABC123"},
        headers=staff_headers,
    )

    response = client.get(
        f"/api/v1/collection-transactions/{transaction_id}/payments", headers=staff_headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_staff_cannot_pay_for_other_points_transaction(admin_headers, staff_headers, transaction_id):
    other_point_resp = client.post(
        "/api/v1/collection-points",
        json={"name": "Pay Other Branch", "address": "2 Test Rd", "county": "Nairobi"},
        headers=admin_headers,
    )
    other_point_id = other_point_resp.json()["id"]

    with SessionLocal() as db:
        other_staff = User(
            email="pay.other.staff@example.com", hashed_password=hash_password(STAFF_PASSWORD),
            full_name="Other Staff", role=UserRole.COLLECTION_POINT_STAFF, collection_point_id=other_point_id,
        )
        db.add(other_staff)
        db.commit()
        db.refresh(other_staff)
        other_staff_id = other_staff.id

    other_headers = _login("pay.other.staff@example.com", STAFF_PASSWORD)

    response = client.post(
        f"/api/v1/collection-transactions/{transaction_id}/payments",
        json={"method": "cash", "amount": 100},
        headers=other_headers,
    )
    assert response.status_code == 403

    with SessionLocal() as db:
        db.query(RefreshToken).filter(RefreshToken.user_id == other_staff_id).delete()
        db.query(User).filter(User.id == other_staff_id).delete()
        db.query(CollectionPoint).filter(CollectionPoint.id == other_point_id).delete()
        db.commit()


def test_admin_can_list_payments(admin_headers, staff_headers, transaction_id):
    client.post(
        f"/api/v1/collection-transactions/{transaction_id}/payments",
        json={"method": "cash", "amount": 100},
        headers=staff_headers,
    )
    response = client.get(
        f"/api/v1/collection-transactions/{transaction_id}/payments", headers=admin_headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
