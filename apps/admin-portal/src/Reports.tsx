import { useEffect, useState } from "react";
import { api, PieChart, TrendChart, RankedBarChart } from "@takaflow/ui";
import type { ReportsByBranchOut, ReportsSummaryOut, ReportsTimeseriesOut } from "@takaflow/types";
import { useCollectionPoints } from "./useCollectionPoints";
import { CashIcon, ChartIcon, DownloadIcon, PackageIcon } from "./icons";

function isoDaysAgo(days: number) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function shortDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

const ALL_BRANCHES = "";

function printReport() {
  window.print();
}

export function Reports() {
  const { points } = useCollectionPoints();
  const [pointId, setPointId] = useState<number | typeof ALL_BRANCHES>(ALL_BRANCHES);
  const [fromDate, setFromDate] = useState(isoDaysAgo(60));
  const [toDate, setToDate] = useState(isoDaysAgo(0));
  const [summary, setSummary] = useState<ReportsSummaryOut | null>(null);
  const [timeseries, setTimeseries] = useState<ReportsTimeseriesOut | null>(null);
  const [byBranch, setByBranch] = useState<ReportsByBranchOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const collectionPointId = pointId === ALL_BRANCHES ? undefined : pointId;
    Promise.all([
      api.getReportsSummary({ fromDate, toDate, collectionPointId }),
      api.getReportsTimeseries({ fromDate, toDate, collectionPointId }),
      pointId === ALL_BRANCHES ? api.getReportsByBranch({ fromDate, toDate }) : Promise.resolve(null),
    ])
      .then(([summaryRes, timeseriesRes, byBranchRes]) => {
        setSummary(summaryRes);
        setTimeseries(timeseriesRes);
        setByBranch(byBranchRes);
      })
      .catch(() => setError("Couldn't load that range."))
      .finally(() => setLoading(false));
  }, [pointId, fromDate, toDate]);

  const branchLabel = pointId === ALL_BRANCHES ? "All branches" : points.find((p) => p.id === pointId)?.name ?? "";

  return (
    <div className="space-y-6">
      {/* Screen-only: filters + PDF trigger. Printing this would be useless on paper. */}
      <div className="flex flex-wrap items-end justify-between gap-4 print:hidden">
        <div className="flex flex-wrap items-end gap-4 rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
          <label className="block">
            <span className="text-xs font-semibold text-ink/60">Branch</span>
            <select
              value={pointId}
              onChange={(e) => setPointId(e.target.value ? Number(e.target.value) : ALL_BRANCHES)}
              className="mt-1 block rounded-xl border border-ink/15 bg-white px-3 py-2 text-sm outline-none focus:border-primary"
            >
              <option value={ALL_BRANCHES}>All branches</option>
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

        <button
          onClick={printReport}
          disabled={!summary}
          className="flex items-center gap-2 rounded-xl bg-forest px-5 py-3 font-bold text-white shadow-sm transition hover:bg-primary disabled:opacity-50"
        >
          <DownloadIcon className="h-4.5 w-4.5" />
          Download PDF
        </button>
      </div>

      {/* Print-only: the filter controls above don't mean anything on paper —
          this is the static context a printed page actually needs instead. */}
      <p className="hidden text-sm text-ink/60 print:block">
        {branchLabel} · {fromDate} to {toDate}
      </p>

      {loading ? (
        <p className="text-sm text-ink/50">Loading…</p>
      ) : error ? (
        <p className="text-sm font-medium text-red-600">{error}</p>
      ) : summary && timeseries ? (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
              <PackageIcon className="mb-2 h-5 w-5 text-forest" />
              <div className="text-sm text-ink/60">Amount collected</div>
              <div className="text-2xl font-extrabold text-ink">{summary.total_collected_quantity.toLocaleString()} kg</div>
            </div>
            <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
              <ChartIcon className="mb-2 h-5 w-5 text-forest" />
              <div className="text-sm text-ink/60">Amount sold</div>
              <div className="text-2xl font-extrabold text-ink">{summary.total_sold_quantity.toLocaleString()} kg</div>
            </div>
            <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
              <CashIcon className="mb-2 h-5 w-5 text-forest" />
              <div className="text-sm text-ink/60">Payments made</div>
              <div className="text-2xl font-extrabold text-ink">KSh {summary.total_payments_amount.toLocaleString()}</div>
            </div>
          </div>

          <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
            <h3 className="mb-1 font-bold text-ink">Collected over time</h3>
            <p className="mb-4 text-sm text-ink/60">
              {pointId === ALL_BRANCHES ? "Every branch combined." : "This branch."} Hover a point for the day's total.
            </p>
            <TrendChart
              data={timeseries.points.map((p) => ({ label: shortDate(p.day), value: p.collected_quantity }))}
              valueFormatter={(v) => `${v.toLocaleString()} kg`}
            />
          </div>

          {pointId === ALL_BRANCHES && byBranch && (
            <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
              <h3 className="mb-1 font-bold text-ink">Collected by branch</h3>
              <p className="mb-4 text-sm text-ink/60">Which branches are driving the most impact in this range.</p>
              <RankedBarChart
                data={byBranch.branches.map((b) => ({ label: b.collection_point_name, value: b.collected_quantity }))}
                valueFormatter={(v) => `${v.toLocaleString()} kg`}
              />
            </div>
          )}

          <div className="grid gap-6 sm:grid-cols-2">
            <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
              <h3 className="mb-4 font-bold text-ink">Collected by material</h3>
              <PieChart
                data={summary.collected_by_material.map((m) => ({ label: m.material_name, value: m.quantity }))}
                valueFormatter={(v) => `${v.toLocaleString()} kg`}
              />
            </div>
            <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
              <h3 className="mb-4 font-bold text-ink">Sold by material</h3>
              <PieChart
                data={summary.sold_by_material.map((m) => ({ label: m.material_name, value: m.quantity }))}
                valueFormatter={(v) => `${v.toLocaleString()} kg`}
              />
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
