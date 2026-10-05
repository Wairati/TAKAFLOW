// Shared TypeScript types mirroring backend Pydantic schemas.
// See docs/architecture-blueprint.html SS08 for the entities these describe.

export type UserRole = "admin" | "collection_point_staff";

export interface UserOut {
  id: number;
  email: string;
  username: string | null;
  employee_number: string | null;
  full_name: string;
  role: UserRole;
  collection_point_id: number | null;
  is_active: boolean;
}

export interface UserCreate {
  email: string;
  username?: string | null;
  employee_number?: string | null;
  password: string;
  full_name: string;
  role: UserRole;
  collection_point_id?: number | null;
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
  /** What we charge a buyer per unit of this material — null until an admin
   * sets one, in which case a buyer-order payment can't be recorded yet. */
  selling_rate: number | null;
}

export interface MaterialUpdate {
  name?: string | null;
  unit?: string | null;
  is_active?: boolean | null;
  selling_rate?: number | null;
}

export interface MaterialRateOut {
  id: number;
  material_id: number;
  collection_point_id: number;
  grade: string | null;
  rate: number;
  effective_from: string;
  effective_to: string | null;
}

export interface AcceptedMaterialOut {
  material: MaterialOut;
  /** One entry per grade currently offered, or a single ungraded entry (grade: null)
   * if this material isn't graded at all. */
  rates: MaterialRateOut[];
}

export interface AcceptMaterialRequest {
  material_id: number;
  rate: number;
  grade?: string | null;
}

export interface SetRateRequest {
  rate: number;
  grade?: string | null;
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
  /** Set for a collaborative collection contributed by a partner
   * organisation — skips pricing entirely, and no payment is ever expected
   * or allowed against the resulting transaction. */
  partner_id?: number | null;
  occurred_at?: string | null;
}

export interface CollectionTransactionOut {
  id: number;
  client_transaction_uuid: string;
  collection_point_id: number;
  material_id: number;
  material_rate_id: number | null;
  rate: number | null;
  recorded_by_user_id: number;
  quantity: number;
  grade: string | null;
  collector_name: string | null;
  collector_phone: string | null;
  partner_id: number | null;
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

export type PaymentMethod = "mpesa" | "cash";

export interface PaymentCreate {
  method: PaymentMethod;
  amount: number;
  reference_number?: string | null;
}

export interface PaymentOut {
  id: number;
  collection_transaction_id: number;
  method: PaymentMethod;
  amount: number;
  reference_number: string | null;
  created_at: string;
}

export interface MaterialTotal {
  material_id: number;
  material_name: string;
  quantity: number;
}

export interface ReportsSummaryOut {
  collection_point_id: number | null;
  from_date: string;
  to_date: string;
  total_collected_quantity: number;
  collected_by_material: MaterialTotal[];
  total_sold_quantity: number;
  sold_by_material: MaterialTotal[];
  total_payments_amount: number;
}

export interface DailyPoint {
  day: string;
  collected_quantity: number;
  sold_quantity: number;
  payments_amount: number;
}

export interface ReportsTimeseriesOut {
  collection_point_id: number | null;
  from_date: string;
  to_date: string;
  points: DailyPoint[];
}

export interface BranchTotal {
  collection_point_id: number;
  collection_point_name: string;
  collected_quantity: number;
  sold_quantity: number;
  payments_amount: number;
}

export interface ReportsByBranchOut {
  from_date: string;
  to_date: string;
  branches: BranchTotal[];
}

// ---- Partners (collaborative collections) ----------------------------------

export interface PartnerOut {
  id: number;
  name: string;
  contact_person: string | null;
  phone: string | null;
  is_active: boolean;
}

export interface PartnerCreate {
  name: string;
  contact_person?: string | null;
  phone?: string | null;
}

export interface PartnerUpdate {
  name?: string;
  contact_person?: string | null;
  phone?: string | null;
  is_active?: boolean;
}

// ---- Buyer orders ------------------------------------------------------------

export type BuyerOrderStatus = "open" | "paid" | "cancelled";

export interface BuyerOrderCreate {
  buyer_name: string;
  buyer_phone?: string | null;
  material_id: number;
  quantity_requested: number;
  notes?: string | null;
  // Required when an admin creates the order; ignored for staff, whose own
  // branch is always used.
  collection_point_id?: number | null;
}

export interface BuyerOrderOut {
  id: number;
  collection_point_id: number;
  collection_point_name: string;
  buyer_name: string;
  buyer_phone: string | null;
  material_id: number;
  material_name: string;
  unit: string;
  quantity_requested: number;
  status: BuyerOrderStatus;
  notes: string | null;
  created_by_user_id: number;
  created_at: string;
}

export interface BuyerOrderPaymentCreate {
  // No amount field — the server computes it from the material's
  // selling_rate * the order's quantity_requested.
  method: PaymentMethod;
  reference_number?: string | null;
}

export interface BuyerOrderPaymentOut {
  id: number;
  buyer_order_id: number;
  amount: number;
  method: PaymentMethod;
  reference_number: string | null;
  recorded_by_user_id: number;
  created_at: string;
}
