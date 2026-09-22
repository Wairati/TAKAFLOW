"""§19: database-level constraint tests — the DB, not application code, is what
actually guarantees inventory correctness. Each test opens a transaction that
is rolled back (via the failure itself, or explicitly) so nothing is left
behind in the real dev database."""

import pytest
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError

from app.db.session import engine
from app.models import CollectionPoint, InventorySummary, Material


@pytest.fixture
def point_and_material():
    with engine.begin() as conn:
        point_id = conn.execute(
            insert(CollectionPoint).values(
                name="Test Point", address="Test Address", county="Nairobi"
            ).returning(CollectionPoint.id)
        ).scalar_one()
        material_id = conn.execute(
            insert(Material).values(name="Test Material", unit="kg").returning(Material.id)
        ).scalar_one()
    yield point_id, material_id
    with engine.begin() as conn:
        conn.execute(InventorySummary.__table__.delete().where(
            InventorySummary.collection_point_id == point_id
        ))
        conn.execute(CollectionPoint.__table__.delete().where(CollectionPoint.id == point_id))
        conn.execute(Material.__table__.delete().where(Material.id == material_id))


def test_negative_on_hand_rejected(point_and_material):
    point_id, material_id = point_and_material
    with pytest.raises(IntegrityError, match="ck_on_hand_non_negative"):
        with engine.begin() as conn:
            conn.execute(
                insert(InventorySummary).values(
                    collection_point_id=point_id,
                    material_id=material_id,
                    quantity_on_hand=-5,
                    quantity_reserved=0,
                )
            )


def test_negative_reserved_rejected(point_and_material):
    point_id, material_id = point_and_material
    with pytest.raises(IntegrityError, match="ck_reserved_non_negative"):
        with engine.begin() as conn:
            conn.execute(
                insert(InventorySummary).values(
                    collection_point_id=point_id,
                    material_id=material_id,
                    quantity_on_hand=0,
                    quantity_reserved=-1,
                )
            )


def test_positive_balances_accepted(point_and_material):
    point_id, material_id = point_and_material
    with engine.begin() as conn:
        conn.execute(
            insert(InventorySummary).values(
                collection_point_id=point_id,
                material_id=material_id,
                quantity_on_hand=10,
                quantity_reserved=2,
            )
        )
