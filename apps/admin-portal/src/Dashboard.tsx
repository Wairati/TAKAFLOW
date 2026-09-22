// Phase 9: "One thin admin view: today's collections + current inventory
// per branch — enough to prove the ledger, not a full dashboard" (blueprint
// §22). Reads real data from Phases 4–8; adds no business logic of its own.
import { useEffect, useState } from "react";
import { api } from "@takaflow/ui";
import type { CollectionPointOut, CollectionTransactionOut, InventorySummaryOut, UserOut } from "@takaflow/types";

function useCollectionPoints() {
  const [points, setPoints] = useState<CollectionPointOut[]>([]);
  useEffect(() => {
    api.listCollectionPoints().then(setPoints).catch(() => setPoints([]));
  }, []);
  const nameById = new Map(points.map((p) => [p.id, p.name]));
  return { points, nameById };
}

export function Dashboard({ user }: { user: UserOut }) {
  const { points, nameById } = useCollectionPoints();
  const [pointFilter, setPointFilter] = useState<number | "">("");
  const [dateFilter, setDateFilter] = useState(new Date().toISOString().slice(0, 10));

  const [summary, setSummary] = useState<InventorySummaryOut[]>([]);
  const [transactions, setTransactions] = useState<CollectionTransactionOut[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.listInventorySummary(pointFilter === "" ? undefined : pointFilter),
      api.listCollectionTransactions({
        collectionPointId: pointFilter === "" ? undefined : pointFilter,
        onDate: dateFilter,
      }),
    ])
      .then(([summaryRows, txRows]) => {
        setSummary(summaryRows);
        setTransactions(txRows);
      })
      .finally(() => setLoading(false));
  }, [pointFilter, dateFilter]);

  const totalQuantityToday = transactions.reduce((sum, t) => sum + t.quantity, 0);

  return (
    <div>
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap", alignItems: "flex-end" }}>
        <label>
          Branch
          <select
            value={pointFilter}
            onChange={(e) => setPointFilter(e.target.value ? Number(e.target.value) : "")}
            style={{ display: "block", padding: "0.4rem" }}
          >
            <option value="">{user.role === "admin" ? "All branches" : "Your branch"}</option>
            {points.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Date
          <input
            type="date"
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            style={{ display: "block", padding: "0.4rem" }}
          />
        </label>
        {loading && <span>Loading…</span>}
      </div>

      <section style={{ marginBottom: "2rem" }}>
        <h2>Current inventory</h2>
        {summary.length === 0 ? (
          <p>No inventory recorded yet for this selection.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #ccc" }}>
                <th>Branch</th>
                <th>Material</th>
                <th>On hand</th>
                <th>Reserved</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {summary.map((row) => (
                <tr key={`${row.collection_point_id}-${row.material_id}`} style={{ borderBottom: "1px solid #eee" }}>
                  <td>{nameById.get(row.collection_point_id) ?? row.collection_point_id}</td>
                  <td>{row.material_name}</td>
                  <td>
                    {row.quantity_on_hand} {row.unit}
                  </td>
                  <td>
                    {row.quantity_reserved} {row.unit}
                  </td>
                  <td>{new Date(row.updated_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section>
        <h2>
          Collections on {dateFilter} <span style={{ fontWeight: "normal", fontSize: "0.9rem" }}>({transactions.length} record{transactions.length === 1 ? "" : "s"}, {totalQuantityToday} total quantity)</span>
        </h2>
        {transactions.length === 0 ? (
          <p>No collections recorded for this date/branch.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #ccc" }}>
                <th>Time</th>
                <th>Branch</th>
                <th>Qty</th>
                <th>Rate</th>
                <th>Grade</th>
                <th>Collector</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((t) => (
                <tr key={t.id} style={{ borderBottom: "1px solid #eee" }}>
                  <td>{new Date(t.occurred_at).toLocaleTimeString()}</td>
                  <td>{nameById.get(t.collection_point_id) ?? t.collection_point_id}</td>
                  <td>{t.quantity}</td>
                  <td>{t.rate}</td>
                  <td>{t.grade ?? "—"}</td>
                  <td>{t.collector_name ?? "walk-in"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
