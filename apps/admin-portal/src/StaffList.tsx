import { Fragment, useEffect, useState } from "react";
import { api } from "@takaflow/ui";
import { ApiError } from "@takaflow/api-client";
import type { UserOut, UserRole } from "@takaflow/types";
import { useCollectionPoints } from "./useCollectionPoints";
import { ResetPasswordForm } from "./ResetPasswordForm";

function extractErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    const detail = (err.detail as { detail?: unknown })?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

export function StaffList({
  refreshKey,
  role,
  title,
  description,
  emptyLabel,
}: {
  refreshKey: number;
  role: UserRole;
  title: string;
  description: string;
  emptyLabel: string;
}) {
  const isStaff = role === "collection_point_staff";
  const { nameById } = useCollectionPoints();
  const [staff, setStaff] = useState<UserOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmingId, setConfirmingId] = useState<number | null>(null);
  const [workingId, setWorkingId] = useState<number | null>(null);
  const [resettingId, setResettingId] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  function load() {
    setLoading(true);
    api
      .listUsers({ role })
      .then(setStaff)
      .finally(() => setLoading(false));
  }

  useEffect(load, [refreshKey, role]);

  async function handleToggleActive(user: UserOut) {
    setError(null);
    setWorkingId(user.id);
    try {
      const updated = user.is_active ? await api.deactivateUser(user.id) : await api.reactivateUser(user.id);
      setStaff((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
      setConfirmingId(null);
    } catch (err) {
      setError(extractErrorMessage(err, "Couldn't update that account — try again."));
    } finally {
      setWorkingId(null);
    }
  }

  return (
    <section className="rounded-2xl border border-ink/10 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-bold text-ink">{title}</h2>
      <p className="mt-1 text-sm text-ink/60">{description}</p>

      {error && <p className="mt-3 text-sm font-medium text-red-600">{error}</p>}
      {notice && <p className="mt-3 text-sm font-medium text-primary">{notice}</p>}

      <div className="mt-5 overflow-x-auto">
        {loading ? (
          <p className="text-sm text-ink/50">Loading…</p>
        ) : staff.length === 0 ? (
          <p className="text-sm text-ink/50">{emptyLabel}</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-black/5 text-ink/50">
                <th className="py-2 font-semibold">Name</th>
                {isStaff && <th className="py-2 font-semibold">Branch</th>}
                {isStaff && <th className="py-2 font-semibold">Employee #</th>}
                <th className="py-2 font-semibold">Email</th>
                <th className="py-2 font-semibold">Status</th>
                <th className="py-2 font-semibold" />
              </tr>
            </thead>
            <tbody>
              {staff.map((s) => (
                <Fragment key={s.id}>
                <tr className="border-b border-black/5">
                  <td className="py-2.5 font-semibold text-ink">{s.full_name}</td>
                  {isStaff && (
                    <td className="py-2.5 text-ink/70">
                      {s.collection_point_id ? nameById.get(s.collection_point_id) ?? s.collection_point_id : "—"}
                    </td>
                  )}
                  {isStaff && <td className="py-2.5 text-ink/70">{s.employee_number ?? "—"}</td>}
                  <td className="py-2.5 text-ink/70">{s.email}</td>
                  <td className="py-2.5">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-bold ${
                        s.is_active ? "bg-mint text-forest" : "bg-red-100 text-red-700"
                      }`}
                    >
                      {s.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="py-2.5 text-right">
                    {confirmingId !== s.id && (
                      <button
                        onClick={() => setResettingId(resettingId === s.id ? null : s.id)}
                        className="mr-2 rounded-lg border border-ink/15 px-2.5 py-1 text-xs font-bold text-ink/70 hover:bg-black/5"
                      >
                        Reset password
                      </button>
                    )}
                    {confirmingId === s.id ? (
                      <span className="inline-flex items-center gap-2">
                        <span className="text-xs text-ink/60">Terminate access?</span>
                        <button
                          onClick={() => handleToggleActive(s)}
                          disabled={workingId === s.id}
                          className="rounded-lg bg-red-600 px-2.5 py-1 text-xs font-bold text-white disabled:opacity-60"
                        >
                          {workingId === s.id ? "…" : "Confirm"}
                        </button>
                        <button
                          onClick={() => setConfirmingId(null)}
                          className="text-xs font-semibold text-ink/50"
                        >
                          Cancel
                        </button>
                      </span>
                    ) : s.is_active ? (
                      <button
                        onClick={() => setConfirmingId(s.id)}
                        className="rounded-lg border border-red-200 px-2.5 py-1 text-xs font-bold text-red-700 hover:bg-red-50"
                      >
                        Deactivate
                      </button>
                    ) : (
                      <button
                        onClick={() => handleToggleActive(s)}
                        disabled={workingId === s.id}
                        className="rounded-lg border border-primary/30 px-2.5 py-1 text-xs font-bold text-primary hover:bg-mint/30 disabled:opacity-60"
                      >
                        {workingId === s.id ? "…" : "Reactivate"}
                      </button>
                    )}
                  </td>
                </tr>
                {resettingId === s.id && (
                  <tr className="border-b border-black/5">
                    <td colSpan={isStaff ? 6 : 4} className="pb-3">
                      <ResetPasswordForm
                        user={s}
                        onCancel={() => setResettingId(null)}
                        onDone={() => {
                          setResettingId(null);
                          setNotice(`Password reset for ${s.full_name}.`);
                        }}
                      />
                    </td>
                  </tr>
                )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
