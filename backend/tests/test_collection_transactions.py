"""§10 / §11 / §19: recording a walk-in collection posts exactly one ledger
entry and updates the summary atomically, and a duplicate client-generated
UUID is idempotent — the two properties this build's correctness story
actually depends on. All against the real database."""

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
from app.models.partner import Partner
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole
from app.services import inventory_service

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
            email="ct.admin@example.com", hashed_password=hash_password(ADMIN_PASSWORD),
            full_name="CT Admin", role=UserRole.ADMIN,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    yield _login("ct.admin@example.com", ADMIN_PASSWORD)

    with SessionLocal() as db:
        db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


@pytest.fixture
def point_with_material(admin_headers):
    """A branch that accepts one material at a known rate — the minimum
    setup a staff member needs before they can record anything."""
    point_resp = client.post(
        "/api/v1/collection-points",
        json={"name": "CT Test Branch", "address": "1 Test Rd", "county": "Nairobi"},
        headers=admin_headers,
    )
    assert point_resp.status_code == 201, point_resp.text
    point_id = point_resp.json()["id"]

    material_resp = client.post(
        "/api/v1/materials", json={"name": "CT Test Material", "unit": "kg"}, headers=admin_headers
    )
    assert material_resp.status_code == 201, material_resp.text
    material_id = material_resp.json()["id"]

    accept_resp = client.post(
        f"/api/v1/collection-points/{point_id}/materials",
        json={"material_id": material_id, "rate": 20.0},
        headers=admin_headers,
    )
    assert accept_resp.status_code == 201, accept_resp.text

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
            email="ct.staff@example.com", hashed_password=hash_password(STAFF_PASSWORD),
            full_name="CT Staff", role=UserRole.COLLECTION_POINT_STAFF, collection_point_id=point_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    yield _login("ct.staff@example.com", STAFF_PASSWORD)

    with SessionLocal() as db:
        # CollectionTransaction.recorded_by_user_id FKs to this user, and this
        # fixture tears down before point_with_material's (reverse of setup
        # order) — so any transaction this staff member created must be
        # cleared here first, or deleting the user violates the FK.
        db.query(CollectionTransaction).filter(CollectionTransaction.recorded_by_user_id == user_id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


def test_admin_cannot_record_collection(admin_headers, point_with_material):
    _, material_id = point_with_material
    response = client.post(
        "/api/v1/collection-transactions",
        json={
            "client_transaction_uuid": str(uuid.uuid4()),
            "material_id": material_id,
            "quantity": 5,
        },
        headers=admin_headers,
    )
    assert response.status_code == 403


def test_record_collection_updates_ledger_and_summary(staff_headers, point_with_material):
    point_id, material_id = point_with_material
    response = client.post(
        "/api/v1/collection-transactions",
        json={
            "client_transaction_uuid": str(uuid.uuid4()),
            "material_id": material_id,
            "quantity": 7.5,
            "collector_name": "Walk-in Collector",
        },
        headers=staff_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["rate"] == 20.0
    assert body["quantity"] == 7.5
    assert body["collection_point_id"] == point_id

    with SessionLocal() as db:
        balance = inventory_service.get_balance(db, point_id, material_id)
        assert balance.quantity_on_hand == Decimal("7.50")


def test_duplicate_client_uuid_is_idempotent(staff_headers, point_with_material):
    point_id, material_id = point_with_material
    txn_uuid = str(uuid.uuid4())
    payload = {"client_transaction_uuid": txn_uuid, "material_id": material_id, "quantity": 3}

    first = client.post("/api/v1/collection-transactions", json=payload, headers=staff_headers)
    assert first.status_code == 201, first.text

    second = client.post("/api/v1/collection-transactions", json=payload, headers=staff_headers)
    assert second.status_code == 201, second.text
    assert second.json()["id"] == first.json()["id"]  # same record, not a new one

    with SessionLocal() as db:
        balance = inventory_service.get_balance(db, point_id, material_id)
        # Not 6 - the duplicate must not have double-counted the inventory.
        assert balance.quantity_on_hand == Decimal("3.00")

        ledger_rows = db.query(InventoryLedger).filter(
            InventoryLedger.collection_point_id == point_id, InventoryLedger.material_id == material_id
        ).all()
        assert len(ledger_rows) == 1


def test_material_not_accepted_at_point_is_rejected(staff_headers, point_with_material):
    with SessionLocal() as db:
        other_material = Material(name="CT Unaccepted Material", unit="kg")
        db.add(other_material)
        db.commit()
        db.refresh(other_material)
        other_material_id = other_material.id

    response = client.post(
        "/api/v1/collection-transactions",
        json={"client_transaction_uuid": str(uuid.uuid4()), "material_id": other_material_id, "quantity": 1},
        headers=staff_headers,
    )
    assert response.status_code == 409

    with SessionLocal() as db:
        db.query(Material).filter(Material.id == other_material_id).delete()
        db.commit()


def test_staff_cannot_view_other_points_transactions(staff_headers, admin_headers):
    other_point_resp = client.post(
        "/api/v1/collection-points",
        json={"name": "CT Other Branch", "address": "2 Test Rd", "county": "Nairobi"},
        headers=admin_headers,
    )
    other_point_id = other_point_resp.json()["id"]

    response = client.get(
        "/api/v1/collection-transactions", params={"collection_point_id": other_point_id}, headers=staff_headers
    )
    assert response.status_code == 403

    with SessionLocal() as db:
        db.query(CollectionPoint).filter(CollectionPoint.id == other_point_id).delete()
        db.commit()


def test_admin_can_list_all_transactions(staff_headers, admin_headers, point_with_material):
    point_id, material_id = point_with_material
    client.post(
        "/api/v1/collection-transactions",
        json={"client_transaction_uuid": str(uuid.uuid4()), "material_id": material_id, "quantity": 2},
        headers=staff_headers,
    )

    response = client.get(
        "/api/v1/collection-transactions", params={"collection_point_id": point_id}, headers=admin_headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_collector_phone_rejects_more_than_ten_digits(staff_headers, point_with_material):
    _, material_id = point_with_material
    response = client.post(
        "/api/v1/collection-transactions",
        json={
            "client_transaction_uuid": str(uuid.uuid4()),
            "material_id": material_id,
            "quantity": 2,
            "collector_phone": "012345678901",
        },
        headers=staff_headers,
    )
    assert response.status_code == 422


def test_collector_phone_rejects_non_digits(staff_headers, point_with_material):
    _, material_id = point_with_material
    response = client.post(
        "/api/v1/collection-transactions",
        json={
            "client_transaction_uuid": str(uuid.uuid4()),
            "material_id": material_id,
            "quantity": 2,
            "collector_phone": "07123 45678",
        },
        headers=staff_headers,
    )
    assert response.status_code == 422


def test_collector_phone_accepts_ten_digits(staff_headers, point_with_material):
    _, material_id = point_with_material
    response = client.post(
        "/api/v1/collection-transactions",
        json={
            "client_transaction_uuid": str(uuid.uuid4()),
            "material_id": material_id,
            "quantity": 2,
            "collector_phone": "0712345678",
        },
        headers=staff_headers,
    )
    assert response.status_code == 201, response.text


# ---- Grade-based pricing ----


def test_different_grades_charge_different_rates(admin_headers, staff_headers, point_with_material):
    point_id, material_id = point_with_material
    client.post(
        f"/api/v1/collection-points/{point_id}/materials",
        json={"material_id": material_id, "rate": 25.0, "grade": "Grade A"},
        headers=admin_headers,
    )
    client.post(
        f"/api/v1/collection-points/{point_id}/materials",
        json={"material_id": material_id, "rate": 8.0, "grade": "Mixed"},
        headers=admin_headers,
    )

    grade_a = client.post(
        "/api/v1/collection-transactions",
        json={
            "client_transaction_uuid": str(uuid.uuid4()),
            "material_id": material_id,
            "quantity": 10,
            "grade": "Grade A",
        },
        headers=staff_headers,
    )
    assert grade_a.status_code == 201, grade_a.text
    assert grade_a.json()["rate"] == 25.0

    mixed = client.post(
        "/api/v1/collection-transactions",
        json={
            "client_transaction_uuid": str(uuid.uuid4()),
            "material_id": material_id,
            "quantity": 10,
            "grade": "Mixed",
        },
        headers=staff_headers,
    )
    assert mixed.status_code == 201, mixed.text
    assert mixed.json()["rate"] == 8.0

    # The material's original ungraded rate (20.0, from the fixture) still
    # works too - graded tiers coexist with it, they don't replace it.
    ungraded = client.post(
        "/api/v1/collection-transactions",
        json={"client_transaction_uuid": str(uuid.uuid4()), "material_id": material_id, "quantity": 10},
        headers=staff_headers,
    )
    assert ungraded.status_code == 201, ungraded.text
    assert ungraded.json()["rate"] == 20.0


def test_unconfigured_grade_is_rejected(staff_headers, point_with_material):
    _, material_id = point_with_material
    response = client.post(
        "/api/v1/collection-transactions",
        json={
            "client_transaction_uuid": str(uuid.uuid4()),
            "material_id": material_id,
            "quantity": 10,
            "grade": "Nonexistent Grade",
        },
        headers=staff_headers,
    )
    assert response.status_code == 409
    assert "not a configured grade" in response.json()["detail"]


def test_grade_required_when_material_has_only_graded_rates(admin_headers, staff_headers, point_with_material):
    point_id, material_id = point_with_material
    # Give this material ONLY a graded rate by retiring the fixture's
    # ungraded one and accepting a graded one in its place.
    client.delete(f"/api/v1/collection-points/{point_id}/materials/{material_id}", headers=admin_headers)
    client.post(
        f"/api/v1/collection-points/{point_id}/materials",
        json={"material_id": material_id, "rate": 25.0, "grade": "Grade A"},
        headers=admin_headers,
    )

    response = client.post(
        "/api/v1/collection-transactions",
        json={"client_transaction_uuid": str(uuid.uuid4()), "material_id": material_id, "quantity": 10},
        headers=staff_headers,
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Select a grade for this material"


# ---- Collaborative collections (partner organisations, no payment) --------


@pytest.fixture
def partner(admin_headers):
    response = client.post(
        "/api/v1/partners", json={"name": "CT Test Conservation Group"}, headers=admin_headers
    )
    assert response.status_code == 201, response.text
    partner_id = response.json()["id"]
    yield partner_id
    with SessionLocal() as db:
        # This fixture doesn't depend on point_with_material, so pytest's
        # LIFO teardown order doesn't guarantee that fixture's
        # CollectionTransaction cleanup has already run — delete any
        # transactions referencing this partner here too, or the FK on
        # collection_transaction.partner_id blocks deleting the row below.
        db.query(CollectionTransaction).filter(CollectionTransaction.partner_id == partner_id).delete()
        db.query(Partner).filter(Partner.id == partner_id).delete()
        db.commit()


def test_collaborative_collection_skips_rate_and_still_updates_inventory(staff_headers, point_with_material, partner):
    point_id, material_id = point_with_material
    response = client.post(
        "/api/v1/collection-transactions",
        json={
            "client_transaction_uuid": str(uuid.uuid4()),
            "material_id": material_id,
            "quantity": 12,
            "partner_id": partner,
        },
        headers=staff_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["partner_id"] == partner
    assert body["material_rate_id"] is None
    assert body["rate"] is None

    summary = client.get(
        "/api/v1/inventory/summary", params={"collection_point_id": point_id}, headers=staff_headers
    ).json()
    assert summary[0]["quantity_on_hand"] == 12.0


def test_collaborative_collection_works_even_with_no_configured_rate(admin_headers, staff_headers, point_with_material, partner):
    point_id, material_id = point_with_material
    # Retire the fixture's rate entirely — a collaborative collection must
    # not require the material to have any priced rate at the branch.
    client.delete(f"/api/v1/collection-points/{point_id}/materials/{material_id}", headers=admin_headers)

    response = client.post(
        "/api/v1/collection-transactions",
        json={
            "client_transaction_uuid": str(uuid.uuid4()),
            "material_id": material_id,
            "quantity": 5,
            "partner_id": partner,
        },
        headers=staff_headers,
    )
    assert response.status_code == 201, response.text


def test_cannot_record_payment_against_a_collaborative_collection(staff_headers, point_with_material, partner):
    _, material_id = point_with_material
    tx_resp = client.post(
        "/api/v1/collection-transactions",
        json={"client_transaction_uuid": str(uuid.uuid4()), "material_id": material_id, "quantity": 5, "partner_id": partner},
        headers=staff_headers,
    )
    tx_id = tx_resp.json()["id"]

    response = client.post(
        f"/api/v1/collection-transactions/{tx_id}/payments",
        json={"method": "cash", "amount": 50},
        headers=staff_headers,
    )
    assert response.status_code == 409
    assert "collaborative" in response.json()["detail"].lower()


def test_inactive_partner_is_rejected(admin_headers, staff_headers, point_with_material, partner):
    _, material_id = point_with_material
    client.patch(f"/api/v1/partners/{partner}", json={"is_active": False}, headers=admin_headers)

    response = client.post(
        "/api/v1/collection-transactions",
        json={"client_transaction_uuid": str(uuid.uuid4()), "material_id": material_id, "quantity": 5, "partner_id": partner},
        headers=staff_headers,
    )
    assert response.status_code == 409
