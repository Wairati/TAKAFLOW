"""Populates realistic-looking demo activity (collections, payments, paid
buyer orders) across every real, active collection point with materials
accepted — so Inventory/History/Reports have something real to show in a
presentation instead of empty states. Any active branch with no staff yet
gets one auto-created (printed at the end) so nothing has to be seeded by
hand first.

Goes through the same service functions the API uses (record_collection,
record_payment, buyer_order_service.create_order/record_payment), so every
ledger/inventory invariant those enforce is respected exactly as it would be
for a real submission — this script never writes transactional data to the
database directly.

Additive, not idempotent: re-running it adds another batch of history on
top of whatever's already there rather than resetting anything.

Usage (from backend/, with the venv active):
    python -m app.scripts.seed_demo_data
"""

import random
import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.collection_point import CollectionPoint
from app.models.material import CollectionPointMaterial, Material
from app.models.payment import PaymentMethod
from app.models.user import User, UserRole
from app.schemas.buyer_order import BuyerOrderCreate, BuyerOrderPaymentCreate
from app.schemas.collection_transaction import CollectionTransactionCreate
from app.schemas.payment import PaymentCreate
from app.services import buyer_order_service, collection_transaction_service, payment_service

# "August and September 2026 to now" - a fixed calendar range rather than a
# rolling window, so the seeded history reads as a real two-month stretch.
START_DATE = datetime(2026, 8, 1, tzinfo=timezone.utc)
END_DATE = datetime.now(timezone.utc)

DEMO_STAFF_PASSWORD = "Demo@2026"  # printed per-account below; change after the demo if it matters

COLLECTOR_NAMES = [
    "Jane Wanjiru", "Peter Otieno", "Grace Achieng", "Samuel Kiprotich", "Mary Njeri",
    "John Mwangi", "Faith Wambui", "David Omondi", "Lucy Chebet", "James Kamau",
    "Esther Adhiambo", "Daniel Kipchoge", "Brian Mutua", "Cynthia Wafula", "Kevin Ochieng",
]
STAFF_NAMES = [
    "Amina Otieno", "Brian Kiptoo", "Caroline Wanjala", "Dennis Mwangi", "Eunice Chebet",
    "Felix Odhiambo", "Grace Nyambura", "Hassan Ali", "Irene Wambui", "Joseph Kariuki",
]
GRADES = [None, None, None, "Grade A", "Mixed"]
BUYERS = ["Mr. Kamau Recyclers", "EcoPlast Ltd", "Nairobi Metal Works", "Green Bottle Buyers"]


def _random_phone() -> str:
    return f"07{random.randint(0, 9)}{random.randint(1000000, 9999999)}"


def _next_employee_number(db: SessionLocal) -> str:
    used = {int(n) for (n,) in db.execute(select(User.employee_number).where(User.employee_number.is_not(None)))}
    candidate = 800001
    while candidate in used:
        candidate += 1
    used.add(candidate)
    return str(candidate)


def _ensure_staff(db: SessionLocal, point: CollectionPoint) -> User:
    staff = db.scalar(
        select(User).where(
            User.collection_point_id == point.id,
            User.role == UserRole.COLLECTION_POINT_STAFF,
            User.is_active.is_(True),
        )
    )
    if staff is not None:
        return staff

    slug = re.sub(r"[^a-z]", "", point.name.lower())
    email = f"staff.{slug}@takaflow.co.ke"
    if db.scalar(select(User).where(User.email == email)) is not None:
        email = f"staff.{slug}.{random.randint(100, 999)}@takaflow.co.ke"

    staff = User(
        email=email,
        employee_number=_next_employee_number(db),
        hashed_password=hash_password(DEMO_STAFF_PASSWORD),
        full_name=random.choice(STAFF_NAMES),
        role=UserRole.COLLECTION_POINT_STAFF,
        collection_point_id=point.id,
    )
    db.add(staff)
    db.flush()
    print(f"  Created staff for {point.name}: {email} / employee #{staff.employee_number} / password {DEMO_STAFF_PASSWORD}")
    return staff


def main() -> None:
    with SessionLocal() as db:
        points = db.query(CollectionPoint).filter(CollectionPoint.is_active.is_(True)).all()
        if not points:
            print("No active collection points found — nothing to seed.")
            return

        total_days = (END_DATE - START_DATE).days
        print(f"Seeding {START_DATE.date()} to {END_DATE.date()} ({total_days} days) across {len(points)} branches.\n")

        for point in points:
            accepted = (
                db.query(CollectionPointMaterial)
                .filter(CollectionPointMaterial.collection_point_id == point.id)
                .all()
            )
            if not accepted:
                print(f"Skipping {point.name}: no accepted materials configured yet.")
                continue

            staff = _ensure_staff(db, point)

            material_names = {
                m.id: m.name for m in db.query(Material).filter(Material.id.in_([a.material_id for a in accepted]))
            }
            print(f"Seeding {point.name} (staff: {staff.full_name}, materials: {', '.join(material_names.values())})...")

            on_hand: dict[int, float] = {a.material_id: 0.0 for a in accepted}
            tx_count = 0
            payment_count = 0
            order_count = 0

            for day_offset in range(total_days, -1, -1):
                day = END_DATE - timedelta(days=day_offset)

                for _ in range(random.randint(1, 4)):
                    cpm = random.choice(accepted)
                    quantity = round(random.uniform(3, 40), 1)
                    occurred_at = day.replace(hour=random.randint(8, 17), minute=random.randint(0, 59), second=0, microsecond=0)

                    tx = collection_transaction_service.record_collection(
                        db,
                        CollectionTransactionCreate(
                            client_transaction_uuid=uuid.uuid4(),
                            material_id=cpm.material_id,
                            quantity=quantity,
                            grade=random.choice(GRADES),
                            collector_name=random.choice(COLLECTOR_NAMES),
                            collector_phone=_random_phone(),
                            occurred_at=occurred_at,
                        ),
                        staff,
                    )
                    tx_count += 1
                    on_hand[cpm.material_id] = on_hand.get(cpm.material_id, 0.0) + quantity

                    # Mostly cash, matching this audience's actual payment mix.
                    if random.random() < 0.85:
                        method = PaymentMethod.CASH if random.random() < 0.8 else PaymentMethod.MPESA
                        payment_service.record_payment(
                            db,
                            tx.id,
                            PaymentCreate(
                                method=method,
                                amount=round(tx.rate * quantity, 2),
                                reference_number=f"S{random.randint(10000000, 99999999)}"
                                if method == PaymentMethod.MPESA
                                else None,
                            ),
                            staff,
                        )
                        payment_count += 1

                # Periodically take and immediately pay a buyer order for a
                # chunk of whatever's accumulated — the same action a staff
                # member performs in the app, which both approves the order
                # and decrements this branch's stock.
                if day_offset % 5 == 0:
                    for cpm in accepted:
                        available = on_hand.get(cpm.material_id, 0.0)
                        if available > 10:
                            order_qty = round(available * random.uniform(0.3, 0.7), 1)
                            order = buyer_order_service.create_order(
                                db,
                                BuyerOrderCreate(
                                    buyer_name=random.choice(BUYERS),
                                    buyer_phone=_random_phone(),
                                    material_id=cpm.material_id,
                                    quantity_requested=order_qty,
                                ),
                                staff,
                            )
                            order_method = random.choice([PaymentMethod.CASH, PaymentMethod.MPESA])
                            buyer_order_service.record_payment(
                                db,
                                order.id,
                                BuyerOrderPaymentCreate(
                                    method=order_method,
                                    amount=round(order_qty * random.uniform(20, 60), 2),
                                    reference_number=f"S{random.randint(10000000, 99999999)}"
                                    if order_method == PaymentMethod.MPESA
                                    else None,
                                ),
                                staff,
                            )
                            on_hand[cpm.material_id] = available - order_qty
                            order_count += 1

            print(f"  {tx_count} collections, {payment_count} payments, {order_count} paid buyer orders recorded.")

        print("\nDone.")


if __name__ == "__main__":
    main()
