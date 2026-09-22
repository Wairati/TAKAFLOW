"""§11 / §19: the actual correctness argument this project is built around.
Everything here runs against the real database - no mocks - including a
genuine multi-connection concurrency test, because the whole point of the
atomic-upsert design is a claim about concurrent writes that a single-
threaded test can't disprove even if it's wrong."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.collection_point import CollectionPoint
from app.models.inventory import InventoryLedger, InventorySummary, MovementType
from app.models.material import Material
from app.services import inventory_service


@pytest.fixture
def point_and_material():
    with SessionLocal() as db:
        point = CollectionPoint(name="Ledger Test Point", address="1 Test Rd", county="Nairobi")
        material = Material(name="Ledger Test Material", unit="kg")
        db.add_all([point, material])
        db.commit()
        db.refresh(point)
        db.refresh(material)
        point_id, material_id = point.id, material.id

    yield point_id, material_id

    with SessionLocal() as db:
        db.query(InventoryLedger).filter(
            InventoryLedger.collection_point_id == point_id, InventoryLedger.material_id == material_id
        ).delete()
        db.query(InventorySummary).filter(
            InventorySummary.collection_point_id == point_id, InventorySummary.material_id == material_id
        ).delete()
        db.query(CollectionPoint).filter(CollectionPoint.id == point_id).delete()
        db.query(Material).filter(Material.id == material_id).delete()
        db.commit()


def test_first_collection_creates_summary_row(point_and_material):
    point_id, material_id = point_and_material
    with SessionLocal() as db:
        inventory_service.post_movement(
            db,
            collection_point_id=point_id,
            material_id=material_id,
            movement_type=MovementType.COLLECTION,
            quantity=10,
            reference_type="collection_transaction",
            reference_id=1,
        )
        db.commit()

        balance = inventory_service.get_balance(db, point_id, material_id)
        assert balance.quantity_on_hand == Decimal("10.00")
        assert balance.quantity_reserved == Decimal("0.00")


def test_sequential_collections_accumulate(point_and_material):
    point_id, material_id = point_and_material
    with SessionLocal() as db:
        for qty in (5, 3, 2):
            inventory_service.post_movement(
                db,
                collection_point_id=point_id,
                material_id=material_id,
                movement_type=MovementType.COLLECTION,
                quantity=qty,
                reference_type="collection_transaction",
                reference_id=qty,
            )
        db.commit()

        balance = inventory_service.get_balance(db, point_id, material_id)
        assert balance.quantity_on_hand == Decimal("10.00")

        ledger_rows = db.scalars(
            select(InventoryLedger).where(
                InventoryLedger.collection_point_id == point_id, InventoryLedger.material_id == material_id
            )
        ).all()
        assert len(ledger_rows) == 3
        assert sum(row.quantity_delta for row in ledger_rows) == balance.quantity_on_hand


def test_adjustment_can_reduce_on_hand(point_and_material):
    point_id, material_id = point_and_material
    with SessionLocal() as db:
        inventory_service.post_movement(
            db, collection_point_id=point_id, material_id=material_id,
            movement_type=MovementType.COLLECTION, quantity=10,
            reference_type="collection_transaction", reference_id=1,
        )
        inventory_service.post_movement(
            db, collection_point_id=point_id, material_id=material_id,
            movement_type=MovementType.ADJUSTMENT, quantity=-4,
            reference_type="manual_correction", reference_id=1,
        )
        db.commit()

        balance = inventory_service.get_balance(db, point_id, material_id)
        assert balance.quantity_on_hand == Decimal("6.00")


def test_adjustment_below_zero_is_rejected_and_rolled_back(point_and_material):
    point_id, material_id = point_and_material
    with SessionLocal() as db:
        inventory_service.post_movement(
            db, collection_point_id=point_id, material_id=material_id,
            movement_type=MovementType.COLLECTION, quantity=5,
            reference_type="collection_transaction", reference_id=1,
        )
        db.commit()

    with pytest.raises(Exception, match="ck_on_hand_non_negative"):
        with SessionLocal() as db:
            inventory_service.post_movement(
                db, collection_point_id=point_id, material_id=material_id,
                movement_type=MovementType.ADJUSTMENT, quantity=-999,
                reference_type="manual_correction", reference_id=2,
            )
            db.commit()

    # The rejected adjustment must not have partially applied.
    with SessionLocal() as db:
        balance = inventory_service.get_balance(db, point_id, material_id)
        assert balance.quantity_on_hand == Decimal("5.00")
        ledger_rows = db.scalars(
            select(InventoryLedger).where(
                InventoryLedger.collection_point_id == point_id, InventoryLedger.material_id == material_id
            )
        ).all()
        assert len(ledger_rows) == 1  # the rejected adjustment left no row behind


def test_concurrent_collections_never_lose_an_update(point_and_material):
    """The actual claim in blueprint SS11: an atomic single-statement UPDATE
    avoids the lost-update race that a read-then-write would produce under
    concurrency. 20 threads, each its own DB connection, each posting +1 at
    the same instant - if the atomic upsert is doing its job, the final
    balance is exactly 20, not something less from two writers reading the
    same starting value and clobbering each other."""
    point_id, material_id = point_and_material
    thread_count = 20

    def post_one(i: int) -> None:
        with SessionLocal() as db:
            inventory_service.post_movement(
                db, collection_point_id=point_id, material_id=material_id,
                movement_type=MovementType.COLLECTION, quantity=1,
                reference_type="collection_transaction", reference_id=i,
            )
            db.commit()

    with ThreadPoolExecutor(max_workers=thread_count) as pool:
        futures = [pool.submit(post_one, i) for i in range(thread_count)]
        for f in as_completed(futures):
            f.result()  # re-raise if any thread's write failed

    with SessionLocal() as db:
        balance = inventory_service.get_balance(db, point_id, material_id)
        assert balance.quantity_on_hand == Decimal(f"{thread_count}.00")

        ledger_rows = db.scalars(
            select(InventoryLedger).where(
                InventoryLedger.collection_point_id == point_id, InventoryLedger.material_id == material_id
            )
        ).all()
        assert len(ledger_rows) == thread_count
        assert sum(row.quantity_delta for row in ledger_rows) == balance.quantity_on_hand
