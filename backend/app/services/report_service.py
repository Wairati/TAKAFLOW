"""Aggregates over the same tables the dashboard's "today" view and the
reports page's "past month" view both read — one function, two callers, so
the timezone-correct date-bucketing logic (see collection_transaction_service
Phase 14 hardening) only has to be written once.

`collection_point_id=None` means "every active branch combined" - only ever
passed that way for an admin request; staff-facing callers always pass their
own branch's id (enforced in the router, not here)."""

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.buyer_order import BuyerOrder, BuyerOrderPayment
from app.models.collection_point import CollectionPoint
from app.models.collection_transaction import CollectionTransaction
from app.models.material import Material
from app.models.payment import Payment
from app.schemas.report import BranchTotal, DailyPoint, MaterialTotal, ReportsByBranchOut, ReportsSummaryOut, ReportsTimeseriesOut

NAIROBI_TZ = "Africa/Nairobi"


def _local_date(column):
    return func.date(func.timezone(NAIROBI_TZ, column))


def _point_filter(column, collection_point_id: int | None):
    return column == collection_point_id if collection_point_id is not None else True


def get_summary(
    db: Session, collection_point_id: int | None, from_date: date, to_date: date
) -> ReportsSummaryOut:
    collected_stmt = (
        select(Material.id, Material.name, func.sum(CollectionTransaction.quantity))
        .join(Material, Material.id == CollectionTransaction.material_id)
        .where(
            _point_filter(CollectionTransaction.collection_point_id, collection_point_id),
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
        select(Material.id, Material.name, func.sum(BuyerOrder.quantity_requested))
        .join(Material, Material.id == BuyerOrder.material_id)
        .join(BuyerOrderPayment, BuyerOrderPayment.buyer_order_id == BuyerOrder.id)
        .where(
            _point_filter(BuyerOrder.collection_point_id, collection_point_id),
            _local_date(BuyerOrderPayment.created_at).between(from_date, to_date),
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
            _point_filter(CollectionTransaction.collection_point_id, collection_point_id),
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


def get_timeseries(
    db: Session, collection_point_id: int | None, from_date: date, to_date: date
) -> ReportsTimeseriesOut:
    collected_day = _local_date(CollectionTransaction.occurred_at).label("day")
    collected_stmt = (
        select(collected_day, func.sum(CollectionTransaction.quantity))
        .where(
            _point_filter(CollectionTransaction.collection_point_id, collection_point_id),
            collected_day.between(from_date, to_date),
        )
        .group_by(collected_day)
    )
    collected_by_day = {day: float(qty) for day, qty in db.execute(collected_stmt).all()}

    sold_day = _local_date(BuyerOrderPayment.created_at).label("day")
    sold_stmt = (
        select(sold_day, func.sum(BuyerOrder.quantity_requested))
        .join(BuyerOrderPayment, BuyerOrderPayment.buyer_order_id == BuyerOrder.id)
        .where(
            _point_filter(BuyerOrder.collection_point_id, collection_point_id),
            sold_day.between(from_date, to_date),
        )
        .group_by(sold_day)
    )
    sold_by_day = {day: float(qty) for day, qty in db.execute(sold_stmt).all()}

    payments_day = _local_date(Payment.created_at).label("day")
    payments_stmt = (
        select(payments_day, func.sum(Payment.amount))
        .join(CollectionTransaction, CollectionTransaction.id == Payment.collection_transaction_id)
        .where(
            _point_filter(CollectionTransaction.collection_point_id, collection_point_id),
            payments_day.between(from_date, to_date),
        )
        .group_by(payments_day)
    )
    payments_by_day = {day: float(amount) for day, amount in db.execute(payments_stmt).all()}

    points = []
    day = from_date
    while day <= to_date:
        points.append(
            DailyPoint(
                day=day,
                collected_quantity=collected_by_day.get(day, 0.0),
                sold_quantity=sold_by_day.get(day, 0.0),
                payments_amount=payments_by_day.get(day, 0.0),
            )
        )
        day += timedelta(days=1)

    return ReportsTimeseriesOut(collection_point_id=collection_point_id, from_date=from_date, to_date=to_date, points=points)


def get_by_branch(db: Session, from_date: date, to_date: date) -> ReportsByBranchOut:
    """Admin-only comparison across every active branch — what makes a
    company-wide "is this working" view possible instead of one branch at a time."""
    collected_stmt = (
        select(CollectionTransaction.collection_point_id, func.sum(CollectionTransaction.quantity))
        .where(_local_date(CollectionTransaction.occurred_at).between(from_date, to_date))
        .group_by(CollectionTransaction.collection_point_id)
    )
    collected_by_point = dict(db.execute(collected_stmt).all())

    sold_stmt = (
        select(BuyerOrder.collection_point_id, func.sum(BuyerOrder.quantity_requested))
        .join(BuyerOrderPayment, BuyerOrderPayment.buyer_order_id == BuyerOrder.id)
        .where(_local_date(BuyerOrderPayment.created_at).between(from_date, to_date))
        .group_by(BuyerOrder.collection_point_id)
    )
    sold_by_point = dict(db.execute(sold_stmt).all())

    payments_stmt = (
        select(CollectionTransaction.collection_point_id, func.sum(Payment.amount))
        .join(CollectionTransaction, CollectionTransaction.id == Payment.collection_transaction_id)
        .where(_local_date(Payment.created_at).between(from_date, to_date))
        .group_by(CollectionTransaction.collection_point_id)
    )
    payments_by_point = dict(db.execute(payments_stmt).all())

    points = db.query(CollectionPoint).filter(CollectionPoint.is_active.is_(True)).order_by(CollectionPoint.name).all()
    branches = [
        BranchTotal(
            collection_point_id=p.id,
            collection_point_name=p.name,
            collected_quantity=float(collected_by_point.get(p.id, 0) or 0),
            sold_quantity=float(sold_by_point.get(p.id, 0) or 0),
            payments_amount=float(payments_by_point.get(p.id, 0) or 0),
        )
        for p in points
    ]

    return ReportsByBranchOut(from_date=from_date, to_date=to_date, branches=branches)
