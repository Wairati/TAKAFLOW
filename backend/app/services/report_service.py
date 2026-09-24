"""Aggregates over the same tables the dashboard's "today" view and the
reports page's "past month" view both read — one function, two callers, so
the timezone-correct date-bucketing logic (see collection_transaction_service
Phase 14 hardening) only has to be written once."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.collection_transaction import CollectionTransaction
from app.models.inventory_sale import InventorySale
from app.models.material import Material
from app.models.payment import Payment
from app.schemas.report import MaterialTotal, ReportsSummaryOut

NAIROBI_TZ = "Africa/Nairobi"


def _local_date(column):
    return func.date(func.timezone(NAIROBI_TZ, column))


def get_summary(db: Session, collection_point_id: int, from_date: date, to_date: date) -> ReportsSummaryOut:
    collected_stmt = (
        select(Material.id, Material.name, func.sum(CollectionTransaction.quantity))
        .join(Material, Material.id == CollectionTransaction.material_id)
        .where(
            CollectionTransaction.collection_point_id == collection_point_id,
            _local_date(CollectionTransaction.occurred_at).between(from_date, to_date),
        )
        .group_by(Material.id, Material.name)
        .order_by(Material.name)
    )
    collected_by_material = [
        MaterialTotal(material_id=mid, material_name=name, quantity=float(qty))
        for mid, name, qty in db.execute(collected_stmt).all()
    ]

    sold_stmt = (
        select(Material.id, Material.name, func.sum(InventorySale.quantity))
        .join(Material, Material.id == InventorySale.material_id)
        .where(
            InventorySale.collection_point_id == collection_point_id,
            _local_date(InventorySale.created_at).between(from_date, to_date),
        )
        .group_by(Material.id, Material.name)
        .order_by(Material.name)
    )
    sold_by_material = [
        MaterialTotal(material_id=mid, material_name=name, quantity=float(qty))
        for mid, name, qty in db.execute(sold_stmt).all()
    ]

    payments_stmt = (
        select(func.coalesce(func.sum(Payment.amount), 0))
        .join(CollectionTransaction, CollectionTransaction.id == Payment.collection_transaction_id)
        .where(
            CollectionTransaction.collection_point_id == collection_point_id,
            _local_date(Payment.created_at).between(from_date, to_date),
        )
    )
    total_payments_amount = float(db.scalar(payments_stmt) or 0)

    return ReportsSummaryOut(
        collection_point_id=collection_point_id,
        from_date=from_date,
        to_date=to_date,
        total_collected_quantity=sum(m.quantity for m in collected_by_material),
        collected_by_material=collected_by_material,
        total_sold_quantity=sum(m.quantity for m in sold_by_material),
        sold_by_material=sold_by_material,
        total_payments_amount=total_payments_amount,
    )
