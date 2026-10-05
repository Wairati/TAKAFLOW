// Recording a walk-in collection (§25 item 7: no supplier registration —
// collector name/phone are optional, free-text, never deduplicated).
// The material dropdown reads from the on-device reference cache, not a
// live API call, so this form works fully offline once materials have
// been fetched at least once (§10).
import { useEffect, useState, type FormEvent } from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { db } from "./db";
import { queueCollection } from "./sync";
import { api, PHONE_MAX_LENGTH, keepDigits } from "@takaflow/ui";
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
  const allMaterialsCache = useLiveQuery(() => db.allMaterialsCache.get("all_materials"), []);
  const partnersCache = useLiveQuery(() => db.partnersCache.get("partners"), []);
  const recent = useLiveQuery(() => db.outbox.orderBy("created_at").reverse().limit(10).toArray(), []) ?? [];
  const [materialId, setMaterialId] = useState<number | "">("");
  const [quantity, setQuantity] = useState("");
  const [grade, setGrade] = useState("");
  const [collectorName, setCollectorName] = useState("");
  const [collectorPhone, setCollectorPhone] = useState("");
  const [isCollaborative, setIsCollaborative] = useState(false);
  const [partnerId, setPartnerId] = useState<number | "">("");
  const [justQueued, setJustQueued] = useState(false);
  const [payingUuid, setPayingUuid] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    api
      .listMaterials(true)
      .then((materials) => db.allMaterialsCache.put({ id: "all_materials", materials, fetched_at: new Date().toISOString() }))
      .catch(() => {});
    api
      .listPartners(true)
      .then((partners) => db.partnersCache.put({ id: "partners", partners, fetched_at: new Date().toISOString() }))
      .catch(() => {});
  }, [user.collection_point_id]);

  const materials = cache?.materials ?? [];
  const allMaterials = allMaterialsCache?.materials ?? [];
  const partners = partnersCache?.partners ?? [];

  const selectedEntry = materials.find((m) => m.material.id === materialId);
  const rates = selectedEntry?.rates ?? [];
  // A material needs an explicit grade choice unless it has exactly one,
  // ungraded price tier — otherwise the backend has no way to know which
  // tier's rate to apply. Not applicable to a collaborative collection,
  // which has no rate at all.
  const needsGrade = !isCollaborative && (rates.length > 1 || (rates.length === 1 && rates[0].grade !== null));
  const selectedRate = needsGrade ? rates.find((r) => (r.grade ?? "") === grade) : rates[0];

  // A collaborative collection isn't limited to materials this branch has a
  // configured (paid) rate for — a partner may bring in anything the branch
  // accepts, priced or not — so its material list is the full catalogue
  // rather than the priced accepted_materials cache.
  const materialOptions = isCollaborative
    ? allMaterials.map((m) => ({ id: m.id, unit: m.unit, label: `${m.name} (${m.unit})` }))
    : materials.map((m) => ({
        id: m.material.id,
        unit: m.material.unit,
        label: `${m.material.name} (${m.material.unit})${
          m.rates.length === 1 ? ` — @${m.rates[0].rate}/${m.material.unit}` : ` — ${m.rates.length} grades`
        }`,
      }));
  const selectedUnit = isCollaborative
    ? allMaterials.find((m) => m.id === materialId)?.unit
    : selectedEntry?.material.unit;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (materialId === "") {
      setError("Please select a material.");
      return;
    }
    if (needsGrade && grade === "") {
      setError("Select a grade for this material.");
      return;
    }
    if (isCollaborative && partnerId === "") {
      setError("Select the partner organisation for this collaborative collection.");
      return;
    }
    if (quantity.trim() === "") {
      setError("Please enter a quantity.");
      return;
    }
    if (!(Number(quantity) > 0)) {
      setError("Quantity must be a number greater than 0.");
      return;
    }

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
        partner_id: isCollaborative ? Number(partnerId) : null,
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
        {materialOptions.length === 0 && (
          <p className="mb-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
            No materials cached yet — connect once to load {isCollaborative ? "the material catalogue" : "your branch's accepted materials"}.
          </p>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="flex items-center gap-2.5 rounded-xl border border-ink/15 bg-mist/20 px-4 py-3">
            <input
              type="checkbox"
              checked={isCollaborative}
              onChange={(e) => {
                setIsCollaborative(e.target.checked);
                setMaterialId("");
                setGrade("");
              }}
              className="h-4 w-4 rounded border-ink/30 text-primary focus:ring-primary/40"
            />
            <span className="text-sm font-semibold text-ink">
              Collaborative collection — from a partner organisation, no payment
            </span>
          </label>
          {isCollaborative && (
            <label className="block">
              <span className="text-sm font-semibold text-ink">Partner organisation</span>
              <select
                value={partnerId}
                onChange={(e) => setPartnerId(e.target.value ? Number(e.target.value) : "")}
                className="mt-1.5 block w-full rounded-xl border border-ink/15 bg-white px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
              >
                <option value="">Select partner…</option>
                {partners.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
              {partners.length === 0 && (
                <span className="mt-1 block text-xs text-amber-700">
                  No partners cached yet — connect once, or ask an admin to add one.
                </span>
              )}
            </label>
          )}
          <label className="block">
            <span className="text-sm font-semibold text-ink">Material</span>
            <select
              value={materialId}
              onChange={(e) => {
                setMaterialId(e.target.value ? Number(e.target.value) : "");
                setGrade("");
              }}
              className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            >
              <option value="">Select material…</option>
              {materialOptions.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
          {needsGrade && (
            <label className="block">
              <span className="text-sm font-semibold text-ink">Grade</span>
              <select
                value={grade}
                onChange={(e) => setGrade(e.target.value)}
                className="mt-1.5 block w-full rounded-xl border border-ink/15 bg-white px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
              >
                <option value="">Select grade…</option>
                {rates.map((r) => (
                  <option key={r.id} value={r.grade ?? ""}>
                    {r.grade ?? "Standard"} — @{r.rate}/{selectedEntry?.material.unit}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className="block">
            <span className="text-sm font-semibold text-ink">
              Quantity ({selectedUnit ?? "unit"})
              {!isCollaborative && selectedRate && ` — @${selectedRate.rate}/${selectedUnit}`}
            </span>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
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
              type="text"
              inputMode="numeric"
              maxLength={PHONE_MAX_LENGTH}
              placeholder="e.g. 0712345678"
              value={collectorPhone}
              onChange={(e) => setCollectorPhone(keepDigits(e.target.value).slice(0, PHONE_MAX_LENGTH))}
              className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </label>
          {error && <p className="text-sm font-medium text-red-600">{error}</p>}
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
              const material =
                materials.find((m) => m.material.id === row.payload.material_id)?.material ??
                allMaterials.find((m) => m.id === row.payload.material_id);
              const isCollaborativeRow = Boolean(row.payload.partner_id);
              const canPay = !isCollaborativeRow && row.status === "synced" && row.result && !row.paid;
              return (
                <li key={row.client_transaction_uuid} className="rounded-xl border border-black/5 p-3.5">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-bold text-ink">
                        {row.payload.quantity} {material?.unit ?? ""} — {material?.name ?? `Material #${row.payload.material_id}`}
                      </div>
                      <div className="text-xs text-ink/50">
                        {isCollaborativeRow
                          ? `Collaborative — no payment${row.status !== "synced" ? ` · ${STATUS_LABEL[row.status] ?? row.status}` : ""}`
                          : row.status === "synced" && row.paid
                            ? "Paid"
                            : STATUS_LABEL[row.status] ?? row.status}
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
