from typing import Literal
import uuid

from pydantic import BaseModel

from app.schemas.collection_transaction import CollectionTransactionCreate, CollectionTransactionOut


class SyncBatchRequest(BaseModel):
    items: list[CollectionTransactionCreate]


class SyncResultItem(BaseModel):
    client_transaction_uuid: uuid.UUID
    status: Literal["synced", "conflict", "error"]
    collection_transaction: CollectionTransactionOut | None = None
    detail: str | None = None


class SyncBatchResponse(BaseModel):
    results: list[SyncResultItem]
