import { useEffect, useState } from "react";
import { api } from "@takaflow/ui";
import type { CollectionTransactionOut } from "@takaflow/types";
import { useCollectionPoints } from "./useCollectionPoints";

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function History() {
  const { points, nameById } = useCollectionPoints();
  const [pointFilter, setPointFilter] = useState<number | "">("");
  const [dateFilter, setDateFilter] = useState(todayIso());
  const [transactions, setTransactions] = useState<CollectionTransactionOut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .listCollectionTransactions({ collectionPointId: pointFilter === "" ? undefined : pointFilter, onDate: dateFilter })
      .then(setTransactions)
      .finally(() => setLoading(false));
  }, [pointFilter, dateFilter]);

  const totalQuantity = transactions.reduce((sum, t) => sum + t.quantity, 0);

  return (
    <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-bold text-ink">Collections on {dateFilter}</h2>
          <p className="text-sm text-ink/60">
            {transactions.length} record{transactions.length === 1 ? "" : "s"} · {totalQuantity.toFixed(1)}kg total
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <label className="block">
            <span className="text-xs font-semibold text-ink/60">Branch</span>
            <select
              value={pointFilter}
              onChange={(e) => setPointFilter(e.target.value ? Number(e.target.value) : "")}
              className="mt-1 block rounded-xl border border-ink/15 bg-white px-3 py-2 text-sm outline-none focus:border-primary"
            >
              <option value="">All branches</option>
              {points.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-semibold text-ink/60">Date</span>
            <input
              type="date"
              value={dateFilter}
              max={todayIso()}
              onChange={(e) => setDateFilter(e.target.value)}
              className="mt-1 block rounded-xl border border-ink/15 px-3 py-2 text-sm outline-none focus:border-primary"
            />
          </label>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-ink/50">Loading…</p>
      ) : transactions.length === 0 ? (
        <p className="text-sm text-ink/50">No collections recorded for this date/branch.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-black/5 text-ink/50">
                <th className="py-2 font-semibold">Time</th>
                <th className="py-2 font-semibold">Branch</th>
                <th className="py-2 font-semibold">Qty</th>
                <th className="py-2 font-semibold">Rate</th>
                <th className="py-2 font-semibold">Grade</th>
                <th className="py-2 font-semibold">Collector</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((t) => (
                <tr key={t.id} className="border-b border-black/5 last:border-0">
                  <td className="py-2.5 text-ink/70">{new Date(t.occurred_at).toLocaleTimeString()}</td>
                  <td className="py-2.5 text-ink/70">{nameById.get(t.collection_point_id) ?? t.collection_point_id}</td>
                  <td className="py-2.5 font-semibold text-ink">{t.quantity}</td>
                  <td className="py-2.5 text-ink/70">KSh {t.rate}</td>
                  <td className="py-2.5 text-ink/70">{t.grade ?? "—"}</td>
                  <td className="py-2.5 text-ink/70">{t.collector_name ?? "Walk-in"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
