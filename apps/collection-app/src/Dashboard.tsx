import { useEffect, useState } from "react";
import { api } from "@takaflow/ui";
import type { CollectionPointOut, CollectionTransactionOut, ReportsSummaryOut, UserOut } from "@takaflow/types";
import { OutboxStatus } from "./OutboxStatus";
import { CashIcon, ClockIcon, PackageIcon, PlusBoxIcon } from "./icons";
import type { Page } from "./App";

const BAR_COLORS = ["bg-primary", "bg-lime", "bg-sky", "bg-olive", "bg-pale-lime"];

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export function Dashboard({
  user,
  branch,
  onNavigate,
}: {
  user: UserOut;
  branch: CollectionPointOut | null;
  onNavigate: (page: Page) => void;
}) {
  const [summary, setSummary] = useState<ReportsSummaryOut | null>(null);
  const [todaysLog, setTodaysLog] = useState<CollectionTransactionOut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user.collection_point_id) {
      setLoading(false);
      return;
    }
    const today = todayIso();
    Promise.all([
      api.getReportsSummary({ fromDate: today, toDate: today, collectionPointId: user.collection_point_id }),
      api.listCollectionTransactions({ collectionPointId: user.collection_point_id, onDate: today }),
    ])
      .then(([summaryRes, txRes]) => {
        setSummary(summaryRes);
        setTodaysLog(txRes);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user.collection_point_id]);

  if (!user.collection_point_id) {
    return (
      <div className="rounded-2xl border border-black/5 bg-white p-6 text-ink/70">
        Your account has no assigned collection point — ask an admin to set one.
      </div>
    );
  }

  const totalPayments = summary?.total_payments_amount ?? 0;
  const totalQuantity = summary?.total_collected_quantity ?? 0;
  const byMaterial = summary?.collected_by_material ?? [];
  const recent = [...todaysLog]
    .sort((a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime())
    .slice(0, 5);

  return (
    <div className="space-y-6">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-2xl">
        <img src="/images/facility.jpg" alt="" className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 bg-forest/60" />
        <div className="relative flex flex-col gap-4 p-6 sm:flex-row sm:items-end sm:justify-between sm:p-8">
          <div>
            <p className="text-lg font-semibold text-white/90">
              {greeting()}, {user.full_name.split(" ")[0]}
            </p>
            <h1 className="mt-1 text-3xl font-extrabold text-white">Keep the cycle moving</h1>
            <p className="mt-1 text-white/80">Every item you collect makes a difference.</p>
          </div>
          <div className="rounded-xl bg-white/95 p-4 shadow-lg">
            <div className="text-sm font-bold text-ink">{branch?.name ?? "Your branch"}</div>
            <div className="text-xs text-ink/60">
              {new Date().toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })} ·{" "}
              {new Date().toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
            </div>
          </div>
        </div>
      </div>

      {/* Stat tiles — real numbers only, no invented day-over-day deltas */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
          <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-mint text-forest">
            <PackageIcon className="h-5 w-5" />
          </div>
          <div className="text-sm text-ink/60">Total Collected Today</div>
          <div className="text-2xl font-extrabold text-ink">{totalQuantity.toFixed(1)} kg</div>
        </div>
        <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
          <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-sky/20 text-sky">
            <PlusBoxIcon className="h-5 w-5" />
          </div>
          <div className="text-sm text-ink/60">Total Transactions</div>
          <div className="text-2xl font-extrabold text-ink">{todaysLog.length}</div>
        </div>
        <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
          <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-pale-lime/60 text-olive">
            <CashIcon className="h-5 w-5" />
          </div>
          <div className="text-sm text-ink/60">Payments Processed</div>
          <div className="text-2xl font-extrabold text-ink">KSh {totalPayments.toLocaleString()}</div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          {/* Today's log */}
          <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-bold text-ink">Today's Collection Log</h2>
              <button onClick={() => onNavigate("history")} className="text-sm font-semibold text-primary">
                View all →
              </button>
            </div>
            {loading ? (
              <p className="text-sm text-ink/50">Loading…</p>
            ) : todaysLog.length === 0 ? (
              <p className="text-sm text-ink/50">No collections logged yet today.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-black/5 text-ink/50">
                      <th className="py-2 font-semibold">Time</th>
                      <th className="py-2 font-semibold">Quantity</th>
                      <th className="py-2 font-semibold">Collector</th>
                    </tr>
                  </thead>
                  <tbody>
                    {todaysLog.slice(0, 8).map((t) => (
                      <tr key={t.id} className="border-b border-black/5 last:border-0">
                        <td className="py-2.5 text-ink/70">
                          {new Date(t.occurred_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
                        </td>
                        <td className="py-2.5 font-semibold text-ink">{t.quantity} kg</td>
                        <td className="py-2.5 text-ink/70">{t.collector_name ?? "Walk-in"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Collections by material */}
          <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
            <h2 className="mb-4 font-bold text-ink">Collections by Material — Today</h2>
            {byMaterial.length === 0 ? (
              <p className="text-sm text-ink/50">Nothing collected yet today.</p>
            ) : (
              <div className="space-y-3">
                {byMaterial.map((m, i) => {
                  const pct = totalQuantity > 0 ? (m.quantity / totalQuantity) * 100 : 0;
                  return (
                    <div key={m.material_id}>
                      <div className="mb-1 flex justify-between text-sm">
                        <span className="font-medium text-ink">{m.material_name}</span>
                        <span className="text-ink/60">
                          {m.quantity} kg ({pct.toFixed(0)}%)
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-black/5">
                        <div
                          className={`h-full rounded-full ${BAR_COLORS[i % BAR_COLORS.length]}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          {/* Quick actions */}
          <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
            <h2 className="mb-4 font-bold text-ink">Quick Actions</h2>
            <div className="grid grid-cols-2 gap-3">
              {[
                { page: "log-collection" as Page, label: "Log Collection", icon: PlusBoxIcon },
                { page: "inventory" as Page, label: "View Inventory", icon: PackageIcon },
                { page: "collectors" as Page, label: "Collectors", icon: CashIcon },
                { page: "history" as Page, label: "History", icon: ClockIcon },
              ].map((action) => (
                <button
                  key={action.page}
                  onClick={() => onNavigate(action.page)}
                  className="flex flex-col items-start gap-2 rounded-xl border border-black/5 p-3.5 text-left transition hover:border-primary/30 hover:bg-mint/20"
                >
                  <action.icon className="h-5 w-5 text-forest" />
                  <span className="text-sm font-semibold text-ink">{action.label}</span>
                </button>
              ))}
            </div>
          </div>

          <OutboxStatus />

          {/* Recent activity — real, derived from today's actual transactions */}
          <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
            <h2 className="mb-3 font-bold text-ink">Recent Activity</h2>
            {recent.length === 0 ? (
              <p className="text-sm text-ink/50">Nothing yet today.</p>
            ) : (
              <ul className="space-y-3">
                {recent.map((t) => (
                  <li key={t.id} className="flex items-start justify-between gap-3 text-sm">
                    <div>
                      <div className="font-semibold text-ink">Collection logged</div>
                      <div className="text-ink/60">
                        {t.quantity} kg from {t.collector_name ?? "walk-in"}
                      </div>
                    </div>
                    <span className="shrink-0 text-xs text-ink/40">
                      {new Date(t.occurred_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* Closing banner */}
      <div className="grid gap-4 overflow-hidden rounded-2xl border border-black/5 bg-white shadow-sm sm:grid-cols-2">
        <div className="flex flex-col justify-center gap-3 p-6">
          <h2 className="text-lg font-bold text-ink">Together for a circular economy</h2>
          <p className="text-sm leading-relaxed text-ink/60">
            You're part of a bigger movement. Your work helps reduce waste, support local communities, and create
            value from recyclable materials.
          </p>
          <button onClick={() => onNavigate("inventory")} className="w-fit text-sm font-bold text-primary">
            View inventory →
          </button>
        </div>
        <img src="/images/facility.jpg" alt="TAKAFLOW facility" className="h-48 w-full object-cover sm:h-full" />
      </div>
    </div>
  );
}
