"""§11: the append-only ledger is the source of truth; inventory_summary is a
derived, fast-read cache of it, kept correct by a single atomic UPDATE per
write — never a read-then-write in application code. This is deliberately the
only place in the codebase allowed to touch inventory_summary directly."""

from sqlalchemy import func, update as sql_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.inventory import InventoryLedger, InventorySummary, MovementType


def _summary_deltas(movement_type: MovementType, quantity: float) -> tuple[float, float]:
    """Returns (on_hand_delta, reserved_delta) for one movement of `quantity`.

    RESERVATION/RESERVATION_RELEASE/TRANSFER_OUT exist for matching/transfers
    (deferred, blueprint SS22) and aren't exercised by any code in this build
    yet - implemented now so the ledger's shape and arithmetic don't need
    revisiting when that work resumes. COLLECTION and ADJUSTMENT are the only
    two actually posted today.
    """
    if movement_type == MovementType.COLLECTION:
        if quantity <= 0:
            raise ValueError("A collection quantity must be positive")
        return quantity, 0
    if movement_type == MovementType.ADJUSTMENT:
        return quantity, 0  # signed: a downward correction is a negative quantity
    if movement_type == MovementType.RESERVATION:
        if quantity <= 0:
            raise ValueError("A reservation quantity must be positive")
        return -quantity, quantity
    if movement_type == MovementType.RESERVATION_RELEASE:
        if quantity <= 0:
            raise ValueError("A reservation-release quantity must be positive")
        return quantity, -quantity
    if movement_type == MovementType.TRANSFER_OUT:
        if quantity <= 0:
            raise ValueError("A transfer-out quantity must be positive")
        return 0, -quantity
    raise ValueError(f"Unhandled movement type: {movement_type}")


def _apply_summary_delta(
    db: Session, collection_point_id: int, material_id: int, on_hand_delta: float, reserved_delta: float
) -> None:
    """Atomic UPDATE first; INSERT only if no row exists yet.

    Deliberately NOT "INSERT ... ON CONFLICT DO UPDATE": Postgres validates a
    CHECK constraint against that statement's raw VALUES tuple during its
    speculative-insert phase, before it even knows whether there's a
    conflict - so a perfectly valid negative *delta* (e.g. an adjustment on
    top of a healthy existing balance) can be rejected even though the real
    resulting balance would never go negative. Confirmed directly against
    Postgres (a throwaway table with the same CHECK reproduced it), not
    assumed - see test_inventory_service.py::test_adjustment_can_reduce_on_hand.
    A plain atomic UPDATE checks the constraint against the real computed
    row, which is what we actually want.
    """
    update_stmt = (
        sql_update(InventorySummary)
        .where(
            InventorySummary.collection_point_id == collection_point_id,
            InventorySummary.material_id == material_id,
        )
        .values(
            quantity_on_hand=InventorySummary.quantity_on_hand + on_hand_delta,
            quantity_reserved=InventorySummary.quantity_reserved + reserved_delta,
            updated_at=func.now(),
        )
    )
    if db.execute(update_stmt).rowcount > 0:
        return

    # First-ever movement for this (point, material): a plain INSERT is safe
    # here, since Postgres validates the CHECK constraint against these exact
    # starting values - which is exactly right (a first movement can't start
    # the balance negative).
    insert_stmt = InventorySummary.__table__.insert().values(
        collection_point_id=collection_point_id,
        material_id=material_id,
        quantity_on_hand=on_hand_delta,
        quantity_reserved=reserved_delta,
    )
    try:
        with db.begin_nested():  # SAVEPOINT: a lost race here rolls back only this insert
            db.execute(insert_stmt)
    except IntegrityError:
        # Either a concurrent writer won the race to insert the first row (a
        # row now exists - retry as the UPDATE above), or this genuinely was
        # an invalid starting balance (no row exists - the retry below
        # affects 0 rows too, and we re-raise the original failure).
        if db.execute(update_stmt).rowcount == 0:
            raise


def post_movement(
    db: Session,
    *,
    collection_point_id: int,
    material_id: int,
    movement_type: MovementType,
    quantity: float,
    reference_type: str,
    reference_id: int,
) -> InventoryLedger:
    """Appends one ledger row and applies its effect to inventory_summary in
    one atomic upsert. Does NOT commit — the caller composes this into a
    larger transaction (e.g. Phase 6: a collection_transaction insert + this
    ledger post + summary update all succeed or fail together) and commits
    once. Constraint violations (e.g. a negative balance) surface on flush,
    inside that same transaction, so nothing partial is ever persisted.
    """
    on_hand_delta, reserved_delta = _summary_deltas(movement_type, quantity)

    ledger_entry = InventoryLedger(
        collection_point_id=collection_point_id,
        material_id=material_id,
        movement_type=movement_type,
        quantity_delta=on_hand_delta,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(ledger_entry)

    _apply_summary_delta(db, collection_point_id, material_id, on_hand_delta, reserved_delta)

    # Flush (not commit) so a CHECK-constraint violation (e.g. negative
    # on-hand) raises here, inside the caller's still-open transaction, where
    # it can be handled or left to roll back everything atomically.
    db.flush()
    return ledger_entry


def get_balance(db: Session, collection_point_id: int, material_id: int) -> InventorySummary | None:
    return db.get(InventorySummary, {"collection_point_id": collection_point_id, "material_id": material_id})


def list_balances_for_point(db: Session, collection_point_id: int) -> list[InventorySummary]:
    from sqlalchemy import select

    stmt = select(InventorySummary).where(InventorySummary.collection_point_id == collection_point_id)
    return list(db.scalars(stmt))
