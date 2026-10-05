import { useEffect, useState } from "react";
import { api } from "@takaflow/ui";
import { ApiError } from "@takaflow/api-client";
import type { BuyerOrderOut, BuyerOrderPaymentOut, BuyerOrderStatus, MaterialOut, UserOut } from "@takaflow/types";
import { useCollectionPoints } from "./useCollectionPoints";

function extractErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    const detail = (err.detail as { detail?: unknown })?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

const STATUS_LABEL: Record<BuyerOrderStatus, string> = {
  open: "Open — awaiting payment",
  paid: "Paid",
  cancelled: "Cancelled",
};

const STATUS_COLOR: Record<BuyerOrderStatus, string> = {
  open: "bg-amber-100 text-amber-800",
  paid: "bg-mint text-forest",
  cancelled: "bg-red-100 text-red-700",
};

const emptyCreateForm = { buyerName: "", buyerPhone: "", materialId: "", quantity: "", notes: "", collectionPointId: "" };

export function BuyerOrders({ user }: { user: UserOut }) {
  const isAdmin = user.role === "admin";
  const { points } = useCollectionPoints();
  const [materials, setMaterials] = useState<MaterialOut[]>([]);
  const [orders, setOrders] = useState<BuyerOrderOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState(emptyCreateForm);
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  function load() {
    setLoading(true);
    api
      .listBuyerOrders()
      .then(setOrders)
      .catch(() => setError("Couldn't load buyer orders — try refreshing."))
      .finally(() => setLoading(false));
  }

  function loadMaterials() {
    return api.listMaterials(true).then(setMaterials).catch(() => setMaterials([]));
  }

  useEffect(() => {
    loadMaterials();
    load();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreateError(null);

    if (createForm.buyerName.trim() === "") {
      setCreateError("Please enter the buyer's name.");
      return;
    }
    if (!createForm.materialId) {
      setCreateError("Select a material.");
      return;
    }
    if (!(Number(createForm.quantity) > 0)) {
      setCreateError("Quantity requested must be a number greater than 0.");
      return;
    }
    if (isAdmin && !createForm.collectionPointId) {
      setCreateError("Select which branch this order is for.");
      return;
    }

    setCreating(true);
    try {
      await api.createBuyerOrder({
        buyer_name: createForm.buyerName.trim(),
        buyer_phone: createForm.buyerPhone || null,
        material_id: Number(createForm.materialId),
        quantity_requested: Number(createForm.quantity),
        notes: createForm.notes || null,
        collection_point_id: isAdmin ? Number(createForm.collectionPointId) : null,
      });
      setCreateForm(emptyCreateForm);
      load();
    } catch (err) {
      setCreateError(extractErrorMessage(err, "Couldn't create that order — please check the fields and try again."));
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-ink/10 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-bold text-ink">Take a new order</h2>
        <p className="mt-1 text-sm text-ink/60">
          Record what a buyer wants and how much. Once their payment comes in, record it here too — that
          marks the order as paid.
        </p>

        <form onSubmit={handleCreate} className="mt-6 grid gap-5 sm:grid-cols-2">
          <label className="block">
            <span className="text-sm font-semibold text-ink">Buyer name</span>
            <input
              type="text"
              value={createForm.buyerName}
              onChange={(e) => setCreateForm({ ...createForm, buyerName: e.target.value })}
              className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-ink">Buyer phone (optional)</span>
            <input
              type="text"
              value={createForm.buyerPhone}
              onChange={(e) => setCreateForm({ ...createForm, buyerPhone: e.target.value })}
              className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </label>

          {isAdmin && (
            <label className="block">
              <span className="text-sm font-semibold text-ink">Branch</span>
              <select
                value={createForm.collectionPointId}
                onChange={(e) => setCreateForm({ ...createForm, collectionPointId: e.target.value })}
                className="mt-1.5 block w-full rounded-xl border border-ink/15 bg-white px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
              >
                <option value="">Select branch…</option>
                {points.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
          )}

          <label className="block">
            <span className="text-sm font-semibold text-ink">Material</span>
            <select
              value={createForm.materialId}
              onChange={(e) => setCreateForm({ ...createForm, materialId: e.target.value })}
              className="mt-1.5 block w-full rounded-xl border border-ink/15 bg-white px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            >
              <option value="">Select material…</option>
              {materials.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} ({m.unit})
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-ink">Quantity requested</span>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={createForm.quantity}
              onChange={(e) => setCreateForm({ ...createForm, quantity: e.target.value })}
              className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </label>

          <label className="block sm:col-span-2">
            <span className="text-sm font-semibold text-ink">Notes (optional)</span>
            <textarea
              value={createForm.notes}
              onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })}
              rows={2}
              className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </label>

          {createError && <p className="sm:col-span-2 text-sm font-medium text-red-600">{createError}</p>}

          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={creating}
              className="rounded-xl bg-forest px-6 py-2.5 font-bold text-white transition hover:bg-primary disabled:opacity-60"
            >
              {creating ? "Creating…" : "Create order"}
            </button>
          </div>
        </form>
      </section>

      <section className="rounded-2xl border border-ink/10 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-bold text-ink">Orders</h2>
        {error && <p className="mt-3 text-sm font-medium text-red-600">{error}</p>}

        <div className="mt-5 space-y-3">
          {loading ? (
            <p className="text-sm text-ink/50">Loading…</p>
          ) : orders.length === 0 ? (
            <p className="text-sm text-ink/50">No buyer orders yet.</p>
          ) : (
            orders.map((order) => (
              <OrderCard
                key={order.id}
                order={order}
                isAdmin={isAdmin}
                materials={materials}
                expanded={expandedId === order.id}
                onToggle={() => setExpandedId(expandedId === order.id ? null : order.id)}
                onChanged={load}
                onMaterialsChanged={loadMaterials}
              />
            ))
          )}
        </div>
      </section>
    </div>
  );
}

function OrderCard({
  order,
  isAdmin,
  materials,
  expanded,
  onToggle,
  onChanged,
  onMaterialsChanged,
}: {
  order: BuyerOrderOut;
  isAdmin: boolean;
  materials: MaterialOut[];
  expanded: boolean;
  onToggle: () => void;
  onChanged: () => void;
  onMaterialsChanged: () => void;
}) {
  const canCancel = isAdmin && order.status === "open";

  return (
    <div className="rounded-xl border border-black/5">
      <button onClick={onToggle} className="flex w-full items-center justify-between gap-3 p-4 text-left">
        <div>
          <div className="font-bold text-ink">
            {order.buyer_name} — {order.quantity_requested} {order.unit} {order.material_name}
          </div>
          <div className="text-xs text-ink/50">
            {order.collection_point_name}
            {order.buyer_phone ? ` · ${order.buyer_phone}` : ""}
          </div>
        </div>
        <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-bold ${STATUS_COLOR[order.status]}`}>
          {STATUS_LABEL[order.status]}
        </span>
      </button>

      {expanded && (
        <div className="border-t border-black/5 p-4">
          <OrderDetail
            order={order}
            canCancel={canCancel}
            isAdmin={isAdmin}
            material={materials.find((m) => m.id === order.material_id)}
            onChanged={onChanged}
            onMaterialsChanged={onMaterialsChanged}
          />
        </div>
      )}
    </div>
  );
}

function OrderDetail({
  order,
  canCancel,
  isAdmin,
  material,
  onChanged,
  onMaterialsChanged,
}: {
  order: BuyerOrderOut;
  canCancel: boolean;
  isAdmin: boolean;
  material: MaterialOut | undefined;
  onChanged: () => void;
  onMaterialsChanged: () => void;
}) {
  const [payments, setPayments] = useState<BuyerOrderPaymentOut[]>([]);
  const [loadingPayments, setLoadingPayments] = useState(true);
  const [payMethod, setPayMethod] = useState<"cash" | "mpesa">("cash");
  const [payReference, setPayReference] = useState("");
  const [payError, setPayError] = useState<string | null>(null);
  const [paySubmitting, setPaySubmitting] = useState(false);

  const [rateInput, setRateInput] = useState("");
  const [settingRate, setSettingRate] = useState(false);
  const [rateError, setRateError] = useState<string | null>(null);

  const [cancelling, setCancelling] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const sellingRate = material?.selling_rate ?? null;
  const computedAmount = sellingRate != null ? sellingRate * order.quantity_requested : null;

  function loadPayments() {
    setLoadingPayments(true);
    api
      .listBuyerOrderPayments(order.id)
      .then(setPayments)
      .finally(() => setLoadingPayments(false));
  }

  useEffect(loadPayments, [order.id]);

  async function handleRecordPayment(e: React.FormEvent) {
    e.preventDefault();
    setPayError(null);
    if (computedAmount == null) {
      setPayError("Set a selling rate for this material before recording payment.");
      return;
    }
    if (payMethod === "mpesa" && !payReference.trim()) {
      setPayError("An M-Pesa payment needs a reference (the confirmation code).");
      return;
    }
    setPaySubmitting(true);
    try {
      await api.recordBuyerOrderPayment(order.id, {
        method: payMethod,
        reference_number: payReference || null,
      });
      setPayReference("");
      loadPayments();
      onChanged();
    } catch (err) {
      setPayError(extractErrorMessage(err, "Couldn't record that payment — try again."));
    } finally {
      setPaySubmitting(false);
    }
  }

  async function handleSetRate(e: React.FormEvent) {
    e.preventDefault();
    setRateError(null);
    if (!material || !(Number(rateInput) > 0)) {
      setRateError("Enter a selling rate greater than 0.");
      return;
    }
    setSettingRate(true);
    try {
      await api.updateMaterial(material.id, { selling_rate: Number(rateInput) });
      setRateInput("");
      onMaterialsChanged();
    } catch (err) {
      setRateError(extractErrorMessage(err, "Couldn't set that rate — try again."));
    } finally {
      setSettingRate(false);
    }
  }

  async function handleCancel() {
    setCancelling(true);
    setActionError(null);
    try {
      await api.cancelBuyerOrder(order.id);
      onChanged();
    } catch (err) {
      setActionError(extractErrorMessage(err, "Couldn't cancel that order — try again."));
    } finally {
      setCancelling(false);
    }
  }

  return (
    <div className="space-y-5">
      {order.notes && <p className="text-sm text-ink/70">{order.notes}</p>}

      <div>
        <h3 className="text-sm font-bold text-ink">Payments</h3>
        {loadingPayments ? (
          <p className="mt-1 text-sm text-ink/50">Loading…</p>
        ) : payments.length === 0 ? (
          <p className="mt-1 text-sm text-ink/50">No payments recorded yet.</p>
        ) : (
          <ul className="mt-1.5 space-y-1.5 text-sm">
            {payments.map((p) => (
              <li key={p.id} className="text-ink/70">
                KSh {p.amount.toLocaleString()} · {p.method}
                {p.reference_number ? ` · ${p.reference_number}` : ""}
              </li>
            ))}
          </ul>
        )}

        {order.status === "open" && (
          <div className="mt-3">
            {computedAmount != null ? (
              <p className="text-sm text-ink/70">
                Amount due: <span className="font-bold text-ink">KSh {computedAmount.toLocaleString()}</span>{" "}
                <span className="text-xs text-ink/50">
                  ({order.quantity_requested} {order.unit} × KSh {sellingRate}/{order.unit})
                </span>
              </p>
            ) : (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                <p>
                  <strong>{order.material_name}</strong> has no selling rate set yet — a payment can't be recorded
                  until one is.
                </p>
                {isAdmin && (
                  <form onSubmit={handleSetRate} className="mt-2 flex gap-2">
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      placeholder={`Rate per ${order.unit} (KSh)`}
                      value={rateInput}
                      onChange={(e) => setRateInput(e.target.value)}
                      className="rounded-lg border border-ink/15 px-3 py-1.5 text-sm text-ink outline-none focus:border-primary"
                    />
                    <button
                      type="submit"
                      disabled={settingRate}
                      className="rounded-lg bg-forest px-3 py-1.5 text-sm font-bold text-white hover:bg-primary disabled:opacity-60"
                    >
                      {settingRate ? "…" : "Set rate"}
                    </button>
                  </form>
                )}
                {rateError && <p className="mt-1.5 text-xs font-medium text-red-600">{rateError}</p>}
              </div>
            )}

            <form onSubmit={handleRecordPayment} className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
              <select
                value={payMethod}
                onChange={(e) => setPayMethod(e.target.value as "cash" | "mpesa")}
                className="rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-primary"
              >
                <option value="cash">Cash</option>
                <option value="mpesa">M-Pesa</option>
              </select>
              <input
                type="text"
                placeholder="Reference (M-Pesa)"
                value={payReference}
                onChange={(e) => setPayReference(e.target.value)}
                className="rounded-lg border border-ink/15 px-3 py-2 text-sm text-ink outline-none focus:border-primary"
              />
              <button
                type="submit"
                disabled={paySubmitting || computedAmount == null}
                className="rounded-lg bg-forest px-3 py-2 text-sm font-bold text-white hover:bg-primary disabled:opacity-60"
              >
                {paySubmitting ? "…" : "Record payment"}
              </button>
              {payError && <p className="col-span-2 text-xs font-medium text-red-600 sm:col-span-3">{payError}</p>}
            </form>
          </div>
        )}
      </div>

      {canCancel && (
        <div>
          <button
            onClick={handleCancel}
            disabled={cancelling}
            className="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-bold text-red-700 hover:bg-red-50 disabled:opacity-60"
          >
            {cancelling ? "…" : "Cancel order"}
          </button>
        </div>
      )}

      {actionError && <p className="text-sm font-medium text-red-600">{actionError}</p>}
    </div>
  );
}
