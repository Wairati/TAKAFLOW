import { useEffect, useState } from "react";
import { api } from "@takaflow/ui";
import type { InventorySummaryOut, UserOut } from "@takaflow/types";
import { PackageIcon } from "./icons";

export function Inventory({ user }: { user: UserOut }) {
  const [summary, setSummary] = useState<InventorySummaryOut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user.collection_point_id) return;
    setLoading(true);
    api
      .listInventorySummary(user.collection_point_id)
      .then(setSummary)
      .finally(() => setLoading(false));
  }, [user.collection_point_id]);

  if (!user.collection_point_id) {
    return (
      <div className="rounded-2xl border border-black/5 bg-white p-6 text-ink/70">
        Your account has no assigned collection point — ask an admin to set one.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-black/5 bg-white p-6 shadow-sm">
      <h2 className="mb-4 font-bold text-ink">What the branch has on hand</h2>
      {loading ? (
        <p className="text-sm text-ink/50">Loading…</p>
      ) : summary.length === 0 ? (
        <p className="text-sm text-ink/50">No inventory recorded yet.</p>
      ) : (
        <ul className="space-y-3">
          {summary.map((row) => (
            <li
              key={row.material_id}
              className="flex items-center justify-between rounded-xl border border-black/5 p-3.5"
            >
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-mint text-forest">
                  <PackageIcon className="h-4.5 w-4.5" />
                </span>
                <span className="font-semibold text-ink">{row.material_name}</span>
              </div>
              <span className="font-bold text-ink">
                {row.quantity_on_hand} {row.unit}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
