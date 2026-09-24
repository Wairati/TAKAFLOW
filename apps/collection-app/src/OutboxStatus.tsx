// The visible half of §10's correctness story: without this, "it's offline-
// safe" is just an unverifiable claim. Live-updates via Dexie's useLiveQuery
// — no polling needed, the UI reacts the instant the sync engine writes a
// status change.
import { useLiveQuery } from "dexie-react-hooks";
import { db, type OutboxStatus as Status } from "./db";
import { useSyncEngine } from "./sync";
import { CloudIcon } from "./icons";

const STATUS_COLORS: Record<Status, string> = {
  pending: "text-amber-600",
  syncing: "text-sky-600",
  synced: "text-primary",
  conflict: "text-orange-600",
  error: "text-red-600",
};

const STATUS_LABELS: Record<Status, string> = {
  pending: "Pending",
  syncing: "Syncing…",
  synced: "Synced",
  conflict: "Conflict",
  error: "Failed (will retry)",
};

export function OutboxStatus() {
  const rows = useLiveQuery(() => db.outbox.orderBy("created_at").reverse().toArray(), []) ?? [];
  const { syncNow, isOnline } = useSyncEngine();

  const counts = rows.reduce<Record<Status, number>>(
    (acc, row) => ({ ...acc, [row.status]: (acc[row.status] ?? 0) + 1 }),
    { pending: 0, syncing: 0, synced: 0, conflict: 0, error: 0 }
  );
  const outstanding = counts.pending + counts.syncing;

  return (
    <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 font-bold text-ink">
          <CloudIcon className="h-5 w-5 text-primary" />
          Sync Status
        </div>
        <span className={`flex items-center gap-1.5 text-xs font-semibold ${isOnline ? "text-primary" : "text-ink/40"}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${isOnline ? "bg-primary" : "bg-ink/30"}`} />
          {isOnline ? "Online" : "Offline"}
        </span>
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-mint/50">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: rows.length ? `${(counts.synced / rows.length) * 100}%` : "0%" }}
        />
      </div>
      <p className="mt-2 text-sm text-ink/60">
        {outstanding > 0 ? `${outstanding} item${outstanding === 1 ? "" : "s"} syncing…` : "Everything is synced."}
      </p>

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs font-semibold">
        {(Object.keys(STATUS_LABELS) as Status[])
          .filter((s) => counts[s] > 0)
          .map((status) => (
            <span key={status} className={STATUS_COLORS[status]}>
              {STATUS_LABELS[status]}: {counts[status]}
            </span>
          ))}
      </div>

      <button
        onClick={syncNow}
        className="mt-4 w-full rounded-xl border border-ink/10 py-2 text-sm font-bold text-ink transition hover:bg-black/5"
      >
        Sync now
      </button>
    </div>
  );
}
