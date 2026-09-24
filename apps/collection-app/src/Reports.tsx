import { useEffect, useState } from "react";
import { api } from "@takaflow/ui";
import type { ReportsSummaryOut, UserOut } from "@takaflow/types";
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

export function Reports({ user }: { user: UserOut }) {
  const [fromDate, setFromDate] = useState(isoDaysAgo(30));
  const [toDate, setToDate] = useState(isoDaysAgo(0));
  const [summary, setSummary] = useState<ReportsSummaryOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user.collection_point_id) return;
    setLoading(true);
    setError(null);
    api
      .getReportsSummary({ fromDate, toDate, collectionPointId: user.collection_point_id })
      .then(setSummary)
      .catch(() => setError("Couldn't load that range."))
      .finally(() => setLoading(false));
  }, [user.collection_point_id, fromDate, toDate]);

  if (!user.collection_point_id) {
    return (
      <div className="rounded-2xl border border-black/5 bg-white p-6 text-ink/70">
        Your account has no assigned collection point — ask an admin to set one.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-4 rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
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

      {loading ? (
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
            <MaterialBreakdown
              title="Collected by material"
              rows={summary.collected_by_material}
              total={summary.total_collected_quantity}
            />
            <MaterialBreakdown title="Sold by material" rows={summary.sold_by_material} total={summary.total_sold_quantity} />
          </div>
        </>
      ) : null}
    </div>
  );
}
