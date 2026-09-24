// A payments-oriented view of today's collectors — who brought material in,
// how much they're owed, and whether they've been paid. No supplier entity:
// "collector" here is just the free-text name/phone already on the
// transaction (§25 item 7), the same terminology the backend already uses.
import { useEffect, useState } from "react";
import { api } from "@takaflow/ui";
import type { CollectionTransactionOut, PaymentOut, UserOut } from "@takaflow/types";
import { RecordPaymentForm } from "./RecordPaymentForm";

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function Collectors({ user }: { user: UserOut }) {
  const [rows, setRows] = useState<CollectionTransactionOut[]>([]);
  const [paymentsByTx, setPaymentsByTx] = useState<Record<number, PaymentOut[]>>({});
  const [loading, setLoading] = useState(true);
  const [payingId, setPayingId] = useState<number | null>(null);

  function load() {
    if (!user.collection_point_id) return;
    setLoading(true);
    api
      .listCollectionTransactions({ collectionPointId: user.collection_point_id, onDate: todayIso() })
      .then(async (transactions) => {
        setRows(transactions);
        const entries = await Promise.all(
          transactions.map(async (t) => [t.id, await api.listPayments(t.id)] as const)
        );
        setPaymentsByTx(Object.fromEntries(entries));
      })
      .finally(() => setLoading(false));
  }

  useEffect(load, [user.collection_point_id]);

  if (!user.collection_point_id) {
    return (
      <div className="rounded-2xl border border-black/5 bg-white p-6 text-ink/70">
        Your account has no assigned collection point — ask an admin to set one.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-black/5 bg-white p-6 shadow-sm">
      <h2 className="mb-1 font-bold text-ink">Today's collectors</h2>
      <p className="mb-4 text-sm text-ink/60">Everyone who brought material in today, and their payment status.</p>

      {loading ? (
        <p className="text-sm text-ink/50">Loading…</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-ink/50">No collections logged today yet.</p>
      ) : (
        <ul className="space-y-3">
          {rows.map((t) => {
            const payments = paymentsByTx[t.id] ?? [];
            const totalPaid = payments.reduce((sum, p) => sum + p.amount, 0);
            const owed = t.rate * t.quantity;
            const isPaid = totalPaid > 0;
            return (
              <li key={t.id} className="rounded-xl border border-black/5 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="font-bold text-ink">{t.collector_name ?? "Walk-in collector"}</div>
                    <div className="text-sm text-ink/60">
                      {t.collector_phone ?? "No phone on record"} · {t.quantity}kg · KSh {owed.toLocaleString()}
                    </div>
                  </div>
                  {isPaid ? (
                    <span className="rounded-full bg-mint px-3 py-1 text-xs font-bold text-forest">
                      Paid ({payments[0].method === "mpesa" ? "M-Pesa" : "Cash"})
                    </span>
                  ) : payingId === t.id ? null : (
                    <button
                      onClick={() => setPayingId(t.id)}
                      className="rounded-lg bg-lime px-3.5 py-1.5 text-xs font-bold text-ink"
                    >
                      Record payment
                    </button>
                  )}
                </div>
                {payingId === t.id && (
                  <RecordPaymentForm
                    transaction={t}
                    onCancel={() => setPayingId(null)}
                    onRecorded={() => {
                      setPayingId(null);
                      load();
                    }}
                  />
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
