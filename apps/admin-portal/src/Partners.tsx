import { useEffect, useState } from "react";
import { api, isValidPhoneNumber, keepDigits, PHONE_MAX_LENGTH } from "@takaflow/ui";
import { ApiError } from "@takaflow/api-client";
import type { PartnerOut } from "@takaflow/types";

function extractErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    const detail = (err.detail as { detail?: unknown })?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

const emptyForm = { name: "", contactPerson: "", phone: "" };

export function Partners() {
  const [partners, setPartners] = useState<PartnerOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [workingId, setWorkingId] = useState<number | null>(null);
  const [listError, setListError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    api
      .listPartners()
      .then(setPartners)
      .catch(() => setListError("Couldn't load partners — try refreshing."))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSuccess(null);

    if (form.name.trim() === "") {
      setFormError("Please enter the partner organisation's name.");
      return;
    }
    if (form.phone && !isValidPhoneNumber(form.phone)) {
      setFormError(`Phone number must be ${PHONE_MAX_LENGTH} digits or fewer.`);
      return;
    }

    setSubmitting(true);
    try {
      await api.createPartner({
        name: form.name.trim(),
        contact_person: form.contactPerson.trim() || null,
        phone: form.phone || null,
      });
      setSuccess(`${form.name} added.`);
      setForm(emptyForm);
      load();
    } catch (err) {
      setFormError(extractErrorMessage(err, "Couldn't add that partner — please check the fields and try again."));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggleActive(partner: PartnerOut) {
    setWorkingId(partner.id);
    setListError(null);
    try {
      const updated = await api.updatePartner(partner.id, { is_active: !partner.is_active });
      setPartners((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
    } catch (err) {
      setListError(extractErrorMessage(err, "Couldn't update that partner — try again."));
    } finally {
      setWorkingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-ink/10 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-bold text-ink">Add a partner organisation</h2>
        <p className="mt-1 text-sm text-ink/60">
          Environmental or conservation organisations the company collaborates with. Staff can select a
          partner when logging a collaborative collection — one where no payment is expected.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 grid gap-5 sm:grid-cols-2">
          <label className="block">
            <span className="text-sm font-semibold text-ink">Organisation name</span>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-ink">Contact person (optional)</span>
            <input
              type="text"
              value={form.contactPerson}
              onChange={(e) => setForm({ ...form, contactPerson: e.target.value })}
              className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-ink">Phone (optional)</span>
            <input
              type="text"
              inputMode="numeric"
              maxLength={PHONE_MAX_LENGTH}
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: keepDigits(e.target.value).slice(0, PHONE_MAX_LENGTH) })}
              className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </label>

          {formError && <p className="sm:col-span-2 text-sm font-medium text-red-600">{formError}</p>}
          {success && <p className="sm:col-span-2 text-sm font-medium text-primary">{success}</p>}

          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={submitting}
              className="rounded-xl bg-forest px-6 py-2.5 font-bold text-white transition hover:bg-primary disabled:opacity-60"
            >
              {submitting ? "Adding…" : "Add partner"}
            </button>
          </div>
        </form>
      </section>

      <section className="rounded-2xl border border-ink/10 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-bold text-ink">Partner organisations</h2>
        {listError && <p className="mt-3 text-sm font-medium text-red-600">{listError}</p>}

        <div className="mt-5 overflow-x-auto">
          {loading ? (
            <p className="text-sm text-ink/50">Loading…</p>
          ) : partners.length === 0 ? (
            <p className="text-sm text-ink/50">No partner organisations yet.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-black/5 text-ink/50">
                  <th className="py-2 font-semibold">Name</th>
                  <th className="py-2 font-semibold">Contact person</th>
                  <th className="py-2 font-semibold">Phone</th>
                  <th className="py-2 font-semibold">Status</th>
                  <th className="py-2 font-semibold" />
                </tr>
              </thead>
              <tbody>
                {partners.map((p) => (
                  <tr key={p.id} className="border-b border-black/5">
                    <td className="py-2.5 font-semibold text-ink">{p.name}</td>
                    <td className="py-2.5 text-ink/70">{p.contact_person ?? "—"}</td>
                    <td className="py-2.5 text-ink/70">{p.phone ?? "—"}</td>
                    <td className="py-2.5">
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-bold ${
                          p.is_active ? "bg-mint text-forest" : "bg-red-100 text-red-700"
                        }`}
                      >
                        {p.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="py-2.5 text-right">
                      <button
                        onClick={() => handleToggleActive(p)}
                        disabled={workingId === p.id}
                        className={`rounded-lg border px-2.5 py-1 text-xs font-bold disabled:opacity-60 ${
                          p.is_active
                            ? "border-red-200 text-red-700 hover:bg-red-50"
                            : "border-primary/30 text-primary hover:bg-mint/30"
                        }`}
                      >
                        {workingId === p.id ? "…" : p.is_active ? "Deactivate" : "Reactivate"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}
