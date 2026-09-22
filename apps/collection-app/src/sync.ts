// §10 lifecycle: PENDING -> SYNCING -> SYNCED / CONFLICT / ERROR(retry).
// Triggers: online/offline events, a periodic timer while the tab is open,
// and a manual "Sync now" call - never relying on any one of them alone,
// because Background Sync API support is unreliable (notably Safari/iOS).
import { useCallback, useEffect, useState } from "react";
import { db, type OutboxRow } from "./db";
import { api } from "@takaflow/ui";

const SYNC_INTERVAL_MS = 30_000;

let syncing = false; // module-level lock: never run two drains concurrently

export async function drainOutbox(): Promise<void> {
  if (syncing || !navigator.onLine) return;
  syncing = true;
  try {
    const pending = await db.outbox.where("status").anyOf("pending", "error").toArray();
    if (pending.length === 0) return;

    await db.outbox.bulkUpdate(pending.map((row) => ({ key: row.client_transaction_uuid, changes: { status: "syncing" } })));

    let response;
    try {
      response = await api.syncCollectionTransactions(pending.map((row) => row.payload));
    } catch {
      // Dropped connection mid-request, or genuinely offline after all -
      // every row that was "syncing" goes back to "pending" for the next
      // trigger. Never left stuck on "syncing" (SS10: a dropped connection
      // leaves an un-acknowledged record PENDING, never half-applied).
      await db.outbox.bulkUpdate(pending.map((row) => ({ key: row.client_transaction_uuid, changes: { status: "pending" } })));
      return;
    }

    const byUuid = new Map(response.results.map((r) => [r.client_transaction_uuid, r]));
    const updates = pending.map((row) => {
      const result = byUuid.get(row.payload.client_transaction_uuid);
      if (!result) {
        // The server didn't return a result for this one - treat as a drop,
        // retry on the next pass rather than guessing at success.
        return { key: row.client_transaction_uuid, changes: { status: "pending" as const } };
      }
      return {
        key: row.client_transaction_uuid,
        changes: {
          status: result.status,
          result: result.collection_transaction,
          last_error: result.detail,
          attempts: row.attempts + 1,
        },
      };
    });
    await db.outbox.bulkUpdate(updates);
  } finally {
    syncing = false;
  }
}

export function useOnlineStatus(): boolean {
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);
  return online;
}

/** Wires up the online-event + periodic-timer triggers. Call once, near the
 * app root, while a session exists. Returns a manual "Sync now" trigger. */
export function useSyncEngine(): { syncNow: () => void; isOnline: boolean } {
  const isOnline = useOnlineStatus();

  const syncNow = useCallback(() => {
    void drainOutbox();
  }, []);

  useEffect(() => {
    window.addEventListener("online", syncNow);
    const timer = setInterval(syncNow, SYNC_INTERVAL_MS);
    syncNow(); // attempt once on mount, in case items were queued while the app was closed
    return () => {
      window.removeEventListener("online", syncNow);
      clearInterval(timer);
    };
  }, [syncNow]);

  return { syncNow, isOnline };
}

export async function queueCollection(row: Omit<OutboxRow, "status" | "attempts" | "last_error" | "result">): Promise<void> {
  await db.outbox.add({ ...row, status: "pending", attempts: 0, last_error: null, result: null });
  void drainOutbox(); // best-effort immediate attempt; the engine above covers the rest
}
