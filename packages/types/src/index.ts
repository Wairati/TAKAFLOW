// Shared TypeScript types mirroring backend Pydantic schemas.
// See docs/architecture-blueprint.html SS08 for the entities these describe.

export type UserRole = "admin" | "collection_point_staff";

export interface UserOut {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  collection_point_id: number | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface MaterialOut {
  id: number;
  name: string;
  unit: string;
  is_active: boolean;
}

export interface MaterialRateOut {
  id: number;
  material_id: number;
  collection_point_id: number;
  rate: number;
  effective_from: string;
  effective_to: string | null;
}

export interface AcceptedMaterialOut {
  material: MaterialOut;
  current_rate: MaterialRateOut;
}

// The shape a collection-transaction submission takes on the wire - the
// same shape whether posted directly (online) or drained from the Dexie
// outbox via the sync batch endpoint (SS10).
export interface CollectionTransactionCreate {
  client_transaction_uuid: string;
  material_id: number;
  quantity: number;
  grade?: string | null;
  collector_name?: string | null;
  collector_phone?: string | null;
  occurred_at?: string | null;
}

export interface CollectionTransactionOut {
  id: number;
  client_transaction_uuid: string;
  collection_point_id: number;
  material_id: number;
  material_rate_id: number;
  rate: number;
  recorded_by_user_id: number;
  quantity: number;
  grade: string | null;
  collector_name: string | null;
  collector_phone: string | null;
  occurred_at: string;
  created_at: string;
}

export type SyncResultStatus = "synced" | "conflict" | "error";

export interface SyncResultItem {
  client_transaction_uuid: string;
  status: SyncResultStatus;
  collection_transaction: CollectionTransactionOut | null;
  detail: string | null;
}

export interface SyncBatchResponse {
  results: SyncResultItem[];
}

export interface CollectionPointOut {
  id: number;
  name: string;
  address: string;
  county: string;
  latitude: number | null;
  longitude: number | null;
  opening_hours: string | null;
  is_active: boolean;
}

// Phase 9: the read view over the Phase 5 ledger-backed balances.
export interface InventorySummaryOut {
  collection_point_id: number;
  material_id: number;
  material_name: string;
  unit: string;
  quantity_on_hand: number;
  quantity_reserved: number;
  updated_at: string;
}
