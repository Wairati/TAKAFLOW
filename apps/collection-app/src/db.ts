// §10: on-device storage via Dexie over IndexedDB. Two stores:
//   - outbox: one row per collection, created offline-first and drained by
//     the sync engine. Never deleted on success — a synced row IS the
//     "today's collections" history, without a separate cache or a round
//     trip to the server.
//   - referenceCache: a read-only mirror of the staff member's accepted
//     materials + current rates, refreshed opportunistically whenever
//     online, so the recording form works fully offline.
import Dexie, { type EntityTable } from "dexie";
import type { AcceptedMaterialOut, CollectionTransactionCreate, CollectionTransactionOut } from "@takaflow/types";

export type OutboxStatus = "pending" | "syncing" | "synced" | "conflict" | "error";

export interface OutboxRow {
  client_transaction_uuid: string; // primary key - the idempotency key itself
  payload: CollectionTransactionCreate;
  status: OutboxStatus;
  attempts: number;
  last_error: string | null;
  created_at: string;
  result: CollectionTransactionOut | null; // populated once status is "synced"
  paid: boolean; // a payment can only be recorded once `result` exists (has a real server id)
}

export interface ReferenceCacheRow {
  id: "accepted_materials"; // singleton row - one staff member, one branch
  collection_point_id: number;
  materials: AcceptedMaterialOut[];
  fetched_at: string;
}

const db = new Dexie("takaflow-collection-app") as Dexie & {
  outbox: EntityTable<OutboxRow, "client_transaction_uuid">;
  referenceCache: EntityTable<ReferenceCacheRow, "id">;
};

db.version(1).stores({
  outbox: "client_transaction_uuid, status, created_at",
  referenceCache: "id",
});

export { db };
