// The visible half of §10's correctness story: without this, "it's offline-
// safe" is just an unverifiable claim. Live-updates via Dexie's useLiveQuery
// — no polling needed, the UI reacts the instant the sync engine writes a
// status change.
import { useLiveQuery } from "dexie-react-hooks";
import { db, type OutboxStatus as Status } from "./db";
import { useSyncEngine } from "./sync";

const STATUS_COLORS: Record<Status, string> = {
  pending: "#a67c00",
  syncing: "#0066cc",
  synced: "#1a7f37",
  conflict: "#b35900",
  error: "#c0392b",
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

  return (
    <section style={{ maxWidth: 480 }}>
      <h2>Sync status</h2>
      <p>
        Connection: <strong style={{ color: isOnline ? "#1a7f37" : "#c0392b" }}>{isOnline ? "online" : "offline"}</strong>
      </p>
      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "0.75rem" }}>
        {(Object.keys(STATUS_LABELS) as Status[]).map((status) => (
          <span key={status} style={{ color: STATUS_COLORS[status] }}>
            {STATUS_LABELS[status]}: {counts[status]}
          </span>
        ))}
      </div>
      <button onClick={syncNow} style={{ padding: "0.4rem 0.8rem", marginBottom: "1rem" }}>
        Sync now
      </button>

      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "1px solid #ccc" }}>
            <th>Material</th>
            <th>Qty</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.client_transaction_uuid} style={{ borderBottom: "1px solid #eee" }}>
              <td>{row.payload.material_id}</td>
              <td>{row.payload.quantity}</td>
              <td style={{ color: STATUS_COLORS[row.status] }} title={row.last_error ?? undefined}>
                {STATUS_LABELS[row.status]}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
