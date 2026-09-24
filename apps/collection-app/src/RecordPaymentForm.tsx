// Payment can only ever be recorded once a collection has synced and has a
// real server id (see db.ts's OutboxRow.result) — this form is only ever
// shown for a transaction that already exists on the server.
import { useState, type FormEvent } from "react";
import { api } from "@takaflow/ui";
import { ApiError } from "@takaflow/api-client";
import type { CollectionTransactionOut, PaymentMethod } from "@takaflow/types";

export function RecordPaymentForm({
  transaction,
  onRecorded,
  onCancel,
}: {
  transaction: CollectionTransactionOut;
  onRecorded: () => void;
  onCancel: () => void;
}) {
  // Cash first: the target audience mostly has no other way to be paid.
  const [method, setMethod] = useState<PaymentMethod>("cash");
  const [amount, setAmount] = useState(String((transaction.rate * transaction.quantity).toFixed(2)));
  const [reference, setReference] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (method === "mpesa" && !reference.trim()) {
      setError("An M-Pesa payment needs the confirmation code");
      return;
    }
    setSubmitting(true);
    try {
      await api.recordPayment(transaction.id, {
        method,
        amount: Number(amount),
        reference_number: method === "mpesa" ? reference.trim() : null,
      });
      onRecorded();
    } catch (err) {
      const detail = err instanceof ApiError ? (err.detail as { detail?: string })?.detail : undefined;
      setError(typeof detail === "string" ? detail : "Couldn't record that payment — try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mt-3 space-y-3 rounded-xl bg-mint/20 p-4">
      <div className="flex gap-2">
        {(["cash", "mpesa"] as PaymentMethod[]).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMethod(m)}
            className={`flex-1 rounded-lg py-2 text-sm font-bold capitalize transition ${
              method === m ? "bg-forest text-white" : "bg-white text-ink/60"
            }`}
          >
            {m === "mpesa" ? "M-Pesa" : "Cash"}
          </button>
        ))}
      </div>

      <label className="block">
        <span className="text-xs font-semibold text-ink/70">Amount (KSh)</span>
        <input
          type="number"
          step="0.01"
          min="0.01"
          required
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          className="mt-1 block w-full rounded-lg border border-ink/15 px-3 py-2 text-sm outline-none focus:border-primary"
        />
      </label>

      {method === "mpesa" && (
        <label className="block">
          <span className="text-xs font-semibold text-ink/70">M-Pesa confirmation code</span>
          <input
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            className="mt-1 block w-full rounded-lg border border-ink/15 px-3 py-2 text-sm outline-none focus:border-primary"
          />
        </label>
      )}

      {error && <p className="text-xs font-medium text-red-600">{error}</p>}

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="flex-1 rounded-lg bg-forest py-2 text-sm font-bold text-white transition hover:bg-primary disabled:opacity-60"
        >
          {submitting ? "Recording…" : "Confirm payment"}
        </button>
        <button type="button" onClick={onCancel} className="rounded-lg px-3 text-sm font-semibold text-ink/50">
          Cancel
        </button>
      </div>
    </form>
  );
}
