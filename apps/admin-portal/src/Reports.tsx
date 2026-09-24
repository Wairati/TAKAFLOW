import { useEffect, useState } from "react";
import { api } from "@takaflow/ui";
import type { ReportsSummaryOut } from "@takaflow/types";
import { useCollectionPoints } from "./useCollectionPoints";
import { CashIcon, ChartIcon, PackageIcon } from "./icons";

function isoDaysAgo(days: number) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function MaterialBreakdown({ title, rows, total }: { title: string; rows: { material_name: string; quantity: number }[]; total: number }) {
  return (
    <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
      <h3 className="mb-3 font-bold text-ink">{title}</h3>
      {rows.length === 0 ? (
        <p className="text-sm text-ink/50">Nothing in this range.</p>
      ) : (
        <ul className="space-y-2">
          {rows.map((r) => (
            <li key={r.material_name} className="flex justify-between text-sm">
              <span className="font-medium text-ink">{r.material_name}</span>
              <span className="text-ink/60">{r.quantity} kg</span>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-3 border-t border-black/5 pt-3 text-sm font-bold text-ink">Total: {total} kg</div>
    </div>
  );
}

export function Reports() {
  const { points } = useCollectionPoints();
  const [pointId, setPointId] = useState<number | "">("");
  const [fromDate, setFromDate] = useState(isoDaysAgo(30));
  const [toDate, setToDate] = useState(isoDaysAgo(0));
  const [summary, setSummary] = useState<ReportsSummaryOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (points.length > 0 && pointId === "") setPointId(points[0].id);
  }, [points, pointId]);

  useEffect(() => {
    if (pointId === "") return;
    setLoading(true);
    setError(null);
    api
      .getReportsSummary({ fromDate, toDate, collectionPointId: pointId })
      .then(setSummary)
      .catch(() => setError("Couldn't load that range."))
      .finally(() => setLoading(false));
  }, [pointId, fromDate, toDate]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-4 rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
        <label className="block">
          <span className="text-xs font-semibold text-ink/60">Branch</span>
          <select
            value={pointId}
            onChange={(e) => setPointId(e.target.value ? Number(e.target.value) : "")}
            className="mt-1 block rounded-xl border border-ink/15 bg-white px-3 py-2 text-sm outline-none focus:border-primary"
          >
            {points.length === 0 && <option value="">No branches yet</option>}
            {points.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="text-xs font-semibold text-ink/60">From</span>
          <input
            type="date"
            value={fromDate}
            max={toDate}
            onChange={(e) => setFromDate(e.target.value)}
            className="mt-1 block rounded-xl border border-ink/15 px-3 py-2 text-sm outline-none focus:border-primary"
          />
        </label>
        <label className="block">
          <span className="text-xs font-semibold text-ink/60">To</span>
          <input
            type="date"
            value={toDate}
            min={fromDate}
            max={isoDaysAgo(0)}
            onChange={(e) => setToDate(e.target.value)}
            className="mt-1 block rounded-xl border border-ink/15 px-3 py-2 text-sm outline-none focus:border-primary"
          />
        </label>
      </div>

      {pointId === "" ? (
        <p className="text-sm text-ink/50">Add a branch first to see reports.</p>
      ) : loading ? (
        <p className="text-sm text-ink/50">Loading…</p>
      ) : error ? (
        <p className="text-sm font-medium text-red-600">{error}</p>
      ) : summary ? (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
              <PackageIcon className="mb-2 h-5 w-5 text-forest" />
              <div className="text-sm text-ink/60">Amount collected</div>
              <div className="text-2xl font-extrabold text-ink">{summary.total_collected_quantity} kg</div>
            </div>
            <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
              <ChartIcon className="mb-2 h-5 w-5 text-forest" />
              <div className="text-sm text-ink/60">Amount sold</div>
              <div className="text-2xl font-extrabold text-ink">{summary.total_sold_quantity} kg</div>
            </div>
            <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
              <CashIcon className="mb-2 h-5 w-5 text-forest" />
              <div className="text-sm text-ink/60">Payments made</div>
              <div className="text-2xl font-extrabold text-ink">KSh {summary.total_payments_amount.toLocaleString()}</div>
            </div>
          </div>

          <div className="grid gap-6 sm:grid-cols-2">
            <MaterialBreakdown title="Collected by material" rows={summary.collected_by_material} total={summary.total_collected_quantity} />
            <MaterialBreakdown title="Sold by material" rows={summary.sold_by_material} total={summary.total_sold_quantity} />
          </div>
        </>
      ) : null}
    </div>
  );
}
