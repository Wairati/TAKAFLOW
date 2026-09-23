"""Phase 14: gaps that only show up at the seams *between* phases, not within
any single one - each of these was found by re-reading the recording path
end to end and asking "what does Phase N assume Phase M already checked?"

- test_deactivated_material_blocks_new_collection /
  test_deactivated_collection_point_blocks_new_collection: closing a
  material_rate row (Phase 4) is not the same as a material or branch being
  active, and Phase 6's record_collection never checked either flag - a
  real gap, fixed alongside these tests, not assumed away.
- test_idempotent_replay_still_works_after_deactivation: proves the fix
  above didn't break SS10's idempotency guarantee for a transaction that
  already succeeded before the deactivation happened.
- test_on_date_filter_respects_nairobi_not_utc_midnight: a timestamp just
  after local midnight must bucket to the local calendar date - relevant
  because this dev machine's Postgres happens to already default to
  Africa/Nairobi, which would have hidden a UTC-vs-local bug entirely.
- test_concurrent_recordings_through_the_api_never_lose_an_update: Phase
  5's concurrency proof was at the service layer; this repeats it through
  the actual HTTP request path two different staff members would use.
- test_rate_change_between_load_and_submit_uses_live_rate_not_stale_cache:
  proves the server never trusts a client-supplied rate - there isn't one
  in the request at all, so a stale cached rate on the device can't leak in.
"""

import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
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
            email="hardening.admin@example.com", hashed_password=hash_password(ADMIN_PASSWORD),
            full_name="Hardening Admin", role=UserRole.ADMIN,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    yield _login("hardening.admin@example.com", ADMIN_PASSWORD)

    with SessionLocal() as db:
        db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


@pytest.fixture
def point_with_material(admin_headers):
    point_resp = client.post(
        "/api/v1/collection-points",
        json={"name": "Hardening Test Branch", "address": "1 Test Rd", "county": "Nairobi"},
        headers=admin_headers,
    )
    point_id = point_resp.json()["id"]
    material_resp = client.post(
        "/api/v1/materials", json={"name": "Hardening Test Material", "unit": "kg"}, headers=admin_headers
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
            email="hardening.staff@example.com", hashed_password=hash_password(STAFF_PASSWORD),
            full_name="Hardening Staff", role=UserRole.COLLECTION_POINT_STAFF, collection_point_id=point_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    yield _login("hardening.staff@example.com", STAFF_PASSWORD)

    with SessionLocal() as db:
        db.query(CollectionTransaction).filter(CollectionTransaction.recorded_by_user_id == user_id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


def test_deactivated_material_blocks_new_collection(admin_headers, staff_headers, point_with_material):
    _, material_id = point_with_material
    client.patch(f"/api/v1/materials/{material_id}", json={"is_active": False}, headers=admin_headers)

    response = client.post(
        "/api/v1/collection-transactions",
        json={"client_transaction_uuid": str(uuid.uuid4()), "material_id": material_id, "quantity": 5},
        headers=staff_headers,
    )
    assert response.status_code == 409


def test_deactivated_collection_point_blocks_new_collection(admin_headers, staff_headers, point_with_material):
    point_id, material_id = point_with_material
    client.patch(f"/api/v1/collection-points/{point_id}", json={"is_active": False}, headers=admin_headers)

    response = client.post(
        "/api/v1/collection-transactions",
        json={"client_transaction_uuid": str(uuid.uuid4()), "material_id": material_id, "quantity": 5},
        headers=staff_headers,
    )
    assert response.status_code == 409

    client.patch(f"/api/v1/collection-points/{point_id}", json={"is_active": True}, headers=admin_headers)


def test_idempotent_replay_still_works_after_deactivation(admin_headers, staff_headers, point_with_material):
    point_id, material_id = point_with_material
    payload = {"client_transaction_uuid": str(uuid.uuid4()), "material_id": material_id, "quantity": 3}

    first = client.post("/api/v1/collection-transactions", json=payload, headers=staff_headers)
    assert first.status_code == 201, first.text

    client.patch(f"/api/v1/materials/{material_id}", json={"is_active": False}, headers=admin_headers)

    # Same UUID, replayed after the material went inactive - must still
    # succeed and return the original record, not a fresh 409.
    replay = client.post("/api/v1/collection-transactions", json=payload, headers=staff_headers)
    assert replay.status_code == 201, replay.text
    assert replay.json()["id"] == first.json()["id"]

    client.patch(f"/api/v1/materials/{material_id}", json={"is_active": True}, headers=admin_headers)


def test_on_date_filter_respects_nairobi_not_utc_midnight(admin_headers, staff_headers, point_with_material):
    point_id, material_id = point_with_material
    # 00:30 EAT on day D is 21:30 UTC on day D-1. A naive UTC func.date()
    # would file this under D-1; the branch's own calendar says D.
    target_day = date.today() + timedelta(days=2)
    just_after_local_midnight = f"{target_day.isoformat()}T00:30:00+03:00"

    response = client.post(
        "/api/v1/collection-transactions",
        json={
            "client_transaction_uuid": str(uuid.uuid4()),
            "material_id": material_id,
            "quantity": 1,
            "occurred_at": just_after_local_midnight,
        },
        headers=staff_headers,
    )
    assert response.status_code == 201, response.text

    on_target_day = client.get(
        "/api/v1/collection-transactions",
        params={"collection_point_id": point_id, "on_date": target_day.isoformat()},
        headers=admin_headers,
    )
    assert len(on_target_day.json()) == 1

    day_before = (target_day - timedelta(days=1)).isoformat()
    on_previous_day = client.get(
        "/api/v1/collection-transactions",
        params={"collection_point_id": point_id, "on_date": day_before},
        headers=admin_headers,
    )
    assert len(on_previous_day.json()) == 0


def test_concurrent_recordings_through_the_api_never_lose_an_update(staff_headers, point_with_material):
    point_id, material_id = point_with_material
    thread_count = 10

    def post_one(_: int):
        return client.post(
            "/api/v1/collection-transactions",
            json={"client_transaction_uuid": str(uuid.uuid4()), "material_id": material_id, "quantity": 1},
            headers=staff_headers,
        )

    with ThreadPoolExecutor(max_workers=thread_count) as pool:
        futures = [pool.submit(post_one, i) for i in range(thread_count)]
        responses = [f.result() for f in as_completed(futures)]

    assert all(r.status_code == 201 for r in responses)

    with SessionLocal() as db:
        balance = inventory_service.get_balance(db, point_id, material_id)
        assert balance.quantity_on_hand == Decimal(f"{thread_count}.00")


def test_rate_change_between_load_and_submit_uses_live_rate_not_stale_cache(
    admin_headers, staff_headers, point_with_material
):
    point_id, material_id = point_with_material
    # Simulates a device that cached rate=20.0 when the form loaded ("load"
    # here is just reading the current rate), then the admin changes it
    # before the staff member actually submits.
    client.patch(
        f"/api/v1/collection-points/{point_id}/materials/{material_id}/rate",
        json={"rate": 35.0},
        headers=admin_headers,
    )

    response = client.post(
        "/api/v1/collection-transactions",
        json={"client_transaction_uuid": str(uuid.uuid4()), "material_id": material_id, "quantity": 2},
        headers=staff_headers,
    )
    assert response.status_code == 201, response.text
    # The request never even carries a rate - the server always looks up
    # whatever is current at insert time, so there's no stale value to use.
    assert response.json()["rate"] == 35.0
