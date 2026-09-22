# Importing every model here registers it on Base.metadata, which is what lets
# Alembic autogenerate (and app.db.base.Base.metadata elsewhere) see all tables.
from app.models.audit_log import AuditLog
from app.models.collection_point import CollectionPoint
from app.models.collection_transaction import CollectionTransaction
from app.models.device import Device
from app.models.inventory import InventoryLedger, InventorySummary
from app.models.material import CollectionPointMaterial, Material, MaterialRate
from app.models.payment import Payment
from app.models.sync_log import SyncLog
from app.models.user import User

__all__ = [
    "AuditLog",
    "CollectionPoint",
    "CollectionPointMaterial",
    "CollectionTransaction",
    "Device",
    "InventoryLedger",
    "InventorySummary",
    "Material",
    "MaterialRate",
    "Payment",
    "SyncLog",
    "User",
]
