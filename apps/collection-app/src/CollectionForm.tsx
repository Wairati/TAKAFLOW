// Recording a walk-in collection (§25 item 7: no supplier registration —
// collector name/phone are optional, free-text, never deduplicated).
// The material dropdown reads from the on-device reference cache, not a
// live API call, so this form works fully offline once materials have
// been fetched at least once (§10).
import { useEffect, useState, type FormEvent } from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { db } from "./db";
import { queueCollection } from "./sync";
import { api } from "@takaflow/ui";
import type { UserOut } from "@takaflow/types";
import { RecordPaymentForm } from "./RecordPaymentForm";
import { CashIcon } from "./icons";

const STATUS_LABEL: Record<string, string> = {
  pending: "Queued — waiting to sync",
  syncing: "Syncing…",
  synced: "Synced",
  conflict: "Conflict",
  error: "Failed — will retry",
};

export function CollectionForm({ user }: { user: UserOut }) {
  const cache = useLiveQuery(() => db.referenceCache.get("accepted_materials"), []);
  const recent = useLiveQuery(() => db.outbox.orderBy("created_at").reverse().limit(10).toArray(), []) ?? [];
  const [materialId, setMaterialId] = useState<number | "">("");
  const [quantity, setQuantity] = useState("");
  const [grade, setGrade] = useState("");
  const [collectorName, setCollectorName] = useState("");
  const [collectorPhone, setCollectorPhone] = useState("");
  const [justQueued, setJustQueued] = useState(false);
  const [payingUuid, setPayingUuid] = useState<string | null>(null);

  useEffect(() => {
    if (!user.collection_point_id || !navigator.onLine) return;
    api
      .listAcceptedMaterials(user.collection_point_id)
      .then((materials) =>
        db.referenceCache.put({
          id: "accepted_materials",
          collection_point_id: user.collection_point_id!,
          materials,
          fetched_at: new Date().toISOString(),
        })
      )
      .catch(() => {
        // Offline or the request failed - the existing cache (if any) still stands.
      });
  }, [user.collection_point_id]);

  const materials = cache?.materials ?? [];

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (materialId === "" || !quantity) return;

    const clientTransactionUuid = crypto.randomUUID();
    await queueCollection({
      client_transaction_uuid: clientTransactionUuid,
      payload: {
        client_transaction_uuid: clientTransactionUuid,
        material_id: Number(materialId),
        quantity: Number(quantity),
        grade: grade || null,
        collector_name: collectorName || null,
        collector_phone: collectorPhone || null,
      },
      created_at: new Date().toISOString(),
    });

    setQuantity("");
    setGrade("");
    setCollectorName("");
    setCollectorPhone("");
    setJustQueued(true);
    setTimeout(() => setJustQueued(false), 2000);
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
        <h2 className="mb-4 font-bold text-ink">Record a collection</h2>
        {materials.length === 0 && (
          <p className="mb-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
            No materials cached yet — connect once to load your branch's accepted materials.
          </p>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block">
            <span className="text-sm font-semibold text-ink">Material</span>
            <select
              value={materialId}
              onChange={(e) => setMaterialId(e.target.value ? Number(e.target.value) : "")}
              required
              className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            >
              <option value="">Select material…</option>
              {materials.map((m) => (
                <option key={m.material.id} value={m.material.id}>
                  {m.material.name} ({m.material.unit}) — @{m.current_rate.rate}/{m.material.unit}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-sm font-semibold text-ink">
              Quantity ({materials.find((m) => m.material.id === materialId)?.material.unit ?? "unit"})
            </span>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              required
              className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </label>
          <label className="block">
            <span className="text-sm font-semibold text-ink">Grade / quality (optional)</span>
            <input
              value={grade}
              onChange={(e) => setGrade(e.target.value)}
              className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </label>
          <label className="block">
            <span className="text-sm font-semibold text-ink">Collector name (optional — walk-in, no registration)</span>
            <input
              value={collectorName}
              onChange={(e) => setCollectorName(e.target.value)}
              className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </label>
          <label className="block">
            <span className="text-sm font-semibold text-ink">Collector phone (optional)</span>
            <input
              value={collectorPhone}
              onChange={(e) => setCollectorPhone(e.target.value)}
              className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </label>
          <button
            type="submit"
            className="w-full rounded-xl bg-forest py-3 font-bold text-white transition hover:bg-primary"
          >
            Record collection
          </button>
          {justQueued && <p className="text-sm font-semibold text-primary">Queued — will sync automatically.</p>}
        </form>
      </div>

      <div className="rounded-2xl border border-black/5 bg-white p-6 shadow-sm">
        <h2 className="mb-4 font-bold text-ink">Recent collections (this device)</h2>
        {recent.length === 0 ? (
          <p className="text-sm text-ink/50">Nothing recorded yet.</p>
        ) : (
          <ul className="space-y-3">
            {recent.map((row) => {
              const material = materials.find((m) => m.material.id === row.payload.material_id)?.material;
              const canPay = row.status === "synced" && row.result && !row.paid;
              return (
                <li key={row.client_transaction_uuid} className="rounded-xl border border-black/5 p-3.5">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-bold text-ink">
                        {row.payload.quantity} {material?.unit ?? ""} — {material?.name ?? `Material #${row.payload.material_id}`}
                      </div>
                      <div className="text-xs text-ink/50">
                        {row.status === "synced" && row.paid ? "Paid" : STATUS_LABEL[row.status] ?? row.status}
                      </div>
                    </div>
                    {canPay && (
                      <button
                        onClick={() => setPayingUuid(row.client_transaction_uuid)}
                        className="flex shrink-0 items-center gap-1.5 rounded-lg bg-lime px-3 py-1.5 text-xs font-bold text-ink"
                      >
                        <CashIcon className="h-4 w-4" />
                        Record payment
                      </button>
                    )}
                  </div>
                  {payingUuid === row.client_transaction_uuid && row.result && (
                    <RecordPaymentForm
                      transaction={row.result}
                      onCancel={() => setPayingUuid(null)}
                      onRecorded={() => {
                        setPayingUuid(null);
                        void db.outbox.update(row.client_transaction_uuid, { paid: true });
                      }}
                    />
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
