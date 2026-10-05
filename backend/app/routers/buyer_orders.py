from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.buyer_order import BuyerOrderStatus
from app.models.user import User, UserRole
from app.schemas.buyer_order import (
    BuyerOrderCreate,
    BuyerOrderOut,
    BuyerOrderPaymentCreate,
    BuyerOrderPaymentOut,
)
from app.services import buyer_order_service

router = APIRouter(prefix="/buyer-orders", tags=["buyer-orders"])


@router.post("", response_model=BuyerOrderOut, status_code=201)
def create_order(
    data: BuyerOrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.COLLECTION_POINT_STAFF)),
) -> BuyerOrderOut:
    return buyer_order_service.create_order(db, data, user)


@router.get("", response_model=list[BuyerOrderOut])
def list_orders(
    status: BuyerOrderStatus | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[BuyerOrderOut]:
    """Company-wide, for both roles — any branch's staff may end up
    taking payment for any order, so everyone sees the same list."""
    return buyer_order_service.list_orders(db, status_filter=status)


@router.get("/{order_id}", response_model=BuyerOrderOut)
def get_order(order_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> BuyerOrderOut:
    return buyer_order_service.get_order(db, order_id)


@router.post("/{order_id}/cancel", response_model=BuyerOrderOut)
def cancel_order(
    order_id: int, db: Session = Depends(get_db), admin: User = Depends(require_role(UserRole.ADMIN))
) -> BuyerOrderOut:
    return buyer_order_service.cancel_order(db, order_id, admin)


@router.post("/{order_id}/payments", response_model=BuyerOrderPaymentOut, status_code=201)
def record_payment(
    order_id: int,
    data: BuyerOrderPaymentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.COLLECTION_POINT_STAFF)),
) -> BuyerOrderPaymentOut:
    """Recording the payment is itself the approval — staff and admins can
    both confirm a buyer's payment themselves, no separate verification
    step."""
    return buyer_order_service.record_payment(db, order_id, data, user)


@router.get("/{order_id}/payments", response_model=list[BuyerOrderPaymentOut])
def list_payments(
    order_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
) -> list[BuyerOrderPaymentOut]:
    return buyer_order_service.list_payments(db, order_id)
