"""§10: the sync endpoint accepts a batch but processes each transaction
independently and returns a per-record result array — a dropped connection
mid-batch leaves whatever didn't get an acknowledged response as PENDING on
the client, never a half-applied batch on the server. One item's failure
must never poison the ones after it, so every item gets its own
try/rollback around collection_transaction_service's normal single-item
path — the exact same path Phase 6's direct online endpoint uses."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.sync import SyncBatchRequest, SyncBatchResponse, SyncResultItem
from app.services import collection_transaction_service


def sync_batch(db: Session, batch: SyncBatchRequest, staff: User) -> SyncBatchResponse:
    results: list[SyncResultItem] = []

    for item in batch.items:
        try:
            out = collection_transaction_service.record_collection(db, item, staff)
            results.append(SyncResultItem(client_transaction_uuid=item.client_transaction_uuid, status="synced", collection_transaction=out))
        except HTTPException as exc:
            db.rollback()
            status_label = "conflict" if exc.status_code == 409 else "error"
            results.append(
                SyncResultItem(
                    client_transaction_uuid=item.client_transaction_uuid,
                    status=status_label,
                    detail=str(exc.detail),
                )
            )
        except Exception:
            db.rollback()
            results.append(
                SyncResultItem(
                    client_transaction_uuid=item.client_transaction_uuid,
                    status="error",
                    detail="This item failed to sync; it can be retried.",
                )
            )

    return SyncBatchResponse(results=results)
