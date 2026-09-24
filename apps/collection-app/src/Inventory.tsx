import { useEffect, useState, type FormEvent } from "react";
import { api } from "@takaflow/ui";
import { ApiError } from "@takaflow/api-client";
import type { InventorySummaryOut, UserOut } from "@takaflow/types";
import { PackageIcon } from "./icons";

export function Inventory({ user }: { user: UserOut }) {
  const [summary, setSummary] = useState<InventorySummaryOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [materialId, setMaterialId] = useState<number | "">("");
  const [quantity, setQuantity] = useState("");
  const [soldTo, setSoldTo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function load() {
    if (!user.collection_point_id) return;
    setLoading(true);
    api
      .listInventorySummary(user.collection_point_id)
      .then(setSummary)
      .finally(() => setLoading(false));
  }

  useEffect(load, [user.collection_point_id]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (materialId === "" || !quantity) return;

    setSubmitting(true);
    try {
      await api.recordInventorySale({
        material_id: Number(materialId),
        quantity: Number(quantity),
        sold_to: soldTo || null,
      });
      setSuccess("Sale recorded.");
      setMaterialId("");
      setQuantity("");
      setSoldTo("");
      load();
    } catch (err) {
      const detail = err instanceof ApiError ? (err.detail as { detail?: string })?.detail : undefined;
      setError(typeof detail === "string" ? detail : "Couldn't record that sale.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!user.collection_point_id) {
    return (
      <div className="rounded-2xl border border-black/5 bg-white p-6 text-ink/70">
        Your account has no assigned collection point — ask an admin to set one.
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
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

      <div className="rounded-2xl border border-black/5 bg-white p-6 shadow-sm">
        <h2 className="mb-1 font-bold text-ink">Record a sale</h2>
        <p className="mb-4 text-sm text-ink/60">Material leaving the branch, sold or dispatched onward.</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block">
            <span className="text-sm font-semibold text-ink">Material</span>
            <select
              value={materialId}
              onChange={(e) => setMaterialId(e.target.value ? Number(e.target.value) : "")}
              required
              className="mt-1.5 block w-full rounded-xl border border-ink/15 bg-white px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            >
              <option value="">Select material…</option>
              {summary.map((row) => (
                <option key={row.material_id} value={row.material_id}>
                  {row.material_name} ({row.quantity_on_hand} {row.unit} on hand)
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-sm font-semibold text-ink">Quantity</span>
            <input
              type="number"
              step="0.01"
              min="0.01"
              required
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </label>
          <label className="block">
            <span className="text-sm font-semibold text-ink">Sold to (optional)</span>
            <input
              value={soldTo}
              onChange={(e) => setSoldTo(e.target.value)}
              placeholder="e.g. a buyer's name"
              className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </label>
          {error && <p className="text-sm font-medium text-red-600">{error}</p>}
          {success && <p className="text-sm font-medium text-primary">{success}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl bg-forest py-3 font-bold text-white transition hover:bg-primary disabled:opacity-60"
          >
            {submitting ? "Recording…" : "Record sale"}
          </button>
        </form>
      </div>
    </div>
  );
}
