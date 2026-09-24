import { useEffect, useState } from "react";
import { api } from "@takaflow/ui";
import type { InventorySummaryOut } from "@takaflow/types";
import { useCollectionPoints } from "./useCollectionPoints";
import { PackageIcon } from "./icons";

export function Inventory() {
  const { points, nameById } = useCollectionPoints();
  const [pointFilter, setPointFilter] = useState<number | "">("");
  const [summary, setSummary] = useState<InventorySummaryOut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .listInventorySummary(pointFilter === "" ? undefined : pointFilter)
      .then(setSummary)
      .finally(() => setLoading(false));
  }, [pointFilter]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4 rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
        <div>
          <h2 className="font-bold text-ink">Inventory across branches</h2>
          <p className="text-sm text-ink/60">What every branch currently has on hand.</p>
        </div>
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
      </div>

      <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
        {loading ? (
          <p className="text-sm text-ink/50">Loading…</p>
        ) : summary.length === 0 ? (
          <p className="text-sm text-ink/50">No inventory recorded yet for this selection.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-black/5 text-ink/50">
                  <th className="py-2 font-semibold">Branch</th>
                  <th className="py-2 font-semibold">Material</th>
                  <th className="py-2 font-semibold">On hand</th>
                  <th className="py-2 font-semibold">Reserved</th>
                  <th className="py-2 font-semibold">Updated</th>
                </tr>
              </thead>
              <tbody>
                {summary.map((row) => (
                  <tr key={`${row.collection_point_id}-${row.material_id}`} className="border-b border-black/5 last:border-0">
                    <td className="py-2.5 text-ink/70">{nameById.get(row.collection_point_id) ?? row.collection_point_id}</td>
                    <td className="py-2.5 font-semibold text-ink">
                      <span className="mr-2 inline-flex h-6 w-6 items-center justify-center rounded-md bg-mint text-forest align-middle">
                        <PackageIcon className="h-3.5 w-3.5" />
                      </span>
                      {row.material_name}
                    </td>
                    <td className="py-2.5 text-ink/70">
                      {row.quantity_on_hand} {row.unit}
                    </td>
                    <td className="py-2.5 text-ink/70">
                      {row.quantity_reserved} {row.unit}
                    </td>
                    <td className="py-2.5 text-ink/50">{new Date(row.updated_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
