from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.sync import SyncBatchRequest, SyncBatchResponse
from app.services import sync_service

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/collection-transactions", response_model=SyncBatchResponse)
def sync_collection_transactions(
    batch: SyncBatchRequest,
    db: Session = Depends(get_db),
    staff: User = Depends(require_role(UserRole.COLLECTION_POINT_STAFF)),
) -> SyncBatchResponse:
    """§10: the collection-app's offline outbox drains here. Each item is
    processed independently (see sync_service) — a duplicate
    client_transaction_uuid is idempotent, exactly as it is on the direct
    single-item endpoint (Phase 6), since both call the same service function."""
    return sync_service.sync_batch(db, batch, staff)
