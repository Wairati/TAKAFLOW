// A cross-branch "today" overview — the admin equivalent of the collection
// app's Dashboard, using the same already-existing endpoints (no new
// aggregation): listCollectionTransactions/listInventorySummary already
// return every branch when called with no collection_point_id, for an admin.
import { useEffect, useState } from "react";
import { api } from "@takaflow/ui";
import type { CollectionTransactionOut, UserOut } from "@takaflow/types";
import { useCollectionPoints } from "./useCollectionPoints";
import { CashIcon, ClockIcon, PackageIcon, PeopleIcon } from "./icons";
import type { Page } from "./App";

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export function Dashboard({ user, onNavigate }: { user: UserOut; onNavigate: (page: Page) => void }) {
  const { points, nameById } = useCollectionPoints();
  const [todaysTx, setTodaysTx] = useState<CollectionTransactionOut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .listCollectionTransactions({ onDate: todayIso() })
      .then(setTodaysTx)
      .finally(() => setLoading(false));
  }, []);

  const totalQuantity = todaysTx.reduce((sum, t) => sum + t.quantity, 0);
  // A collaborative collection (partner_id set) has no rate — it contributes
  // to the day's recovered quantity but not to its priced value.
  const totalValue = todaysTx.reduce((sum, t) => sum + (t.rate ?? 0) * t.quantity, 0);
  const activeBranches = points.filter((p) => p.is_active).length;
  const recent = [...todaysTx]
    .sort((a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime())
    .slice(0, 6);

  return (
    <div className="space-y-6">
      <div className="relative overflow-hidden rounded-2xl">
        <img src="/images/forest-stream.jpg" alt="" className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 bg-forest/60" />
        <div className="relative p-6 sm:p-8">
          <p className="text-lg font-semibold text-white/90">
            {greeting()}, {user.full_name.split(" ")[0]}
          </p>
          <h1 className="mt-1 text-3xl font-extrabold text-white">Every branch, one place</h1>
          <p className="mt-1 text-white/80">Here's what's happening across the network today.</p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
          <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-mint text-forest">
            <PeopleIcon className="h-5 w-5" />
          </div>
          <div className="text-sm text-ink/60">Active Branches</div>
          <div className="text-2xl font-extrabold text-ink">{activeBranches}</div>
        </div>
        <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
          <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-sky/20 text-sky">
            <PackageIcon className="h-5 w-5" />
          </div>
          <div className="text-sm text-ink/60">Collected Today</div>
          <div className="text-2xl font-extrabold text-ink">{totalQuantity.toFixed(1)} kg</div>
        </div>
        <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
          <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-pale-lime/60 text-olive">
            <CashIcon className="h-5 w-5" />
          </div>
          <div className="text-sm text-ink/60">Value Collected Today</div>
          <div className="text-2xl font-extrabold text-ink">KSh {totalValue.toLocaleString()}</div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-bold text-ink">Today across all branches</h2>
            <button onClick={() => onNavigate("history")} className="text-sm font-semibold text-primary">
              View all →
            </button>
          </div>
          {loading ? (
            <p className="text-sm text-ink/50">Loading…</p>
          ) : todaysTx.length === 0 ? (
            <p className="text-sm text-ink/50">No collections logged anywhere yet today.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-black/5 text-ink/50">
                    <th className="py-2 font-semibold">Time</th>
                    <th className="py-2 font-semibold">Branch</th>
                    <th className="py-2 font-semibold">Quantity</th>
                    <th className="py-2 font-semibold">Collector</th>
                  </tr>
                </thead>
                <tbody>
                  {todaysTx.slice(0, 8).map((t) => (
                    <tr key={t.id} className="border-b border-black/5 last:border-0">
                      <td className="py-2.5 text-ink/70">{new Date(t.occurred_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}</td>
                      <td className="py-2.5 text-ink/70">{nameById.get(t.collection_point_id) ?? t.collection_point_id}</td>
                      <td className="py-2.5 font-semibold text-ink">{t.quantity} kg</td>
                      <td className="py-2.5 text-ink/70">{t.collector_name ?? "Walk-in"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
            <h2 className="mb-4 font-bold text-ink">Quick Actions</h2>
            <div className="grid grid-cols-2 gap-3">
              {[
                { page: "staff" as Page, label: "Add Staff", icon: PeopleIcon },
                { page: "inventory" as Page, label: "View Inventory", icon: PackageIcon },
                { page: "history" as Page, label: "History", icon: ClockIcon },
                { page: "reports" as Page, label: "Reports", icon: CashIcon },
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
                        {t.quantity} kg at {nameById.get(t.collection_point_id) ?? "a branch"}
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
    </div>
  );
}
