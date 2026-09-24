import { useEffect, useState } from "react";
import { api } from "@takaflow/ui";
import type { CollectionTransactionOut, UserOut } from "@takaflow/types";

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function History({ user }: { user: UserOut }) {
  const [date, setDate] = useState(todayIso());
  const [rows, setRows] = useState<CollectionTransactionOut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user.collection_point_id) return;
    setLoading(true);
    api
      .listCollectionTransactions({ collectionPointId: user.collection_point_id, onDate: date })
      .then(setRows)
      .finally(() => setLoading(false));
  }, [user.collection_point_id, date]);

  if (!user.collection_point_id) {
    return (
      <div className="rounded-2xl border border-black/5 bg-white p-6 text-ink/70">
        Your account has no assigned collection point — ask an admin to set one.
      </div>
    );
  }

  const totalQuantity = rows.reduce((sum, r) => sum + r.quantity, 0);

  return (
    <div className="rounded-2xl border border-black/5 bg-white p-6 shadow-sm">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-bold text-ink">Collection history</h2>
          <p className="text-sm text-ink/60">
            {rows.length} record{rows.length === 1 ? "" : "s"} · {totalQuantity.toFixed(1)}kg total
          </p>
        </div>
        <label className="block">
          <span className="text-xs font-semibold text-ink/60">Date</span>
          <input
            type="date"
            value={date}
            max={todayIso()}
            onChange={(e) => setDate(e.target.value)}
            className="mt-1 block rounded-xl border border-ink/15 px-3 py-2 text-sm outline-none focus:border-primary"
          />
        </label>
      </div>

      {loading ? (
        <p className="text-sm text-ink/50">Loading…</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-ink/50">No collections recorded on this date.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-black/5 text-ink/50">
                <th className="py-2 font-semibold">Time</th>
                <th className="py-2 font-semibold">Quantity</th>
                <th className="py-2 font-semibold">Grade</th>
                <th className="py-2 font-semibold">Collector</th>
                <th className="py-2 font-semibold">Rate</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((t) => (
                <tr key={t.id} className="border-b border-black/5 last:border-0">
                  <td className="py-2.5 text-ink/70">{new Date(t.occurred_at).toLocaleTimeString()}</td>
                  <td className="py-2.5 font-semibold text-ink">{t.quantity} kg</td>
                  <td className="py-2.5 text-ink/70">{t.grade ?? "—"}</td>
                  <td className="py-2.5 text-ink/70">{t.collector_name ?? "Walk-in"}</td>
                  <td className="py-2.5 text-ink/70">KSh {t.rate}/kg</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
