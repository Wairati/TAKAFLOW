// Admin-only: provisions a new collection-point-staff account. There's no
// self-registration (accounts are provisioned, not signed up for), and the
// backend rejects this call outright for anyone who isn't an admin — this
// form just gives that existing POST /auth/users route a real screen.
import { useEffect, useState, type FormEvent } from "react";
import { ApiError } from "@takaflow/api-client";
import {
  api,
  EMPLOYEE_NUMBER_LENGTH,
  isValidEmployeeNumber,
  keepDigits,
  PASSWORD_RULES,
  isPasswordValid,
} from "@takaflow/ui";
import type { CollectionPointOut } from "@takaflow/types";

function extractErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    const detail = (err.detail as { detail?: unknown })?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  }
  return fallback;
}

const emptyForm = {
  fullName: "",
  email: "",
  employeeNumber: "",
  collectionPointId: "",
  password: "",
  confirmPassword: "",
};

export function CreateStaffForm() {
  const [points, setPoints] = useState<CollectionPointOut[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.listCollectionPoints().then(setPoints).catch(() => setPoints([]));
  }, []);

  const passwordsMatch = form.password.length > 0 && form.password === form.confirmPassword;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!isValidEmployeeNumber(form.employeeNumber)) {
      setError(`Employee number must be exactly ${EMPLOYEE_NUMBER_LENGTH} digits`);
      return;
    }
    if (!form.collectionPointId) {
      setError("Select a branch for this staff member");
      return;
    }
    if (!isPasswordValid(form.password)) {
      setError("Password doesn't meet all the requirements below");
      return;
    }
    if (!passwordsMatch) {
      setError("Passwords don't match");
      return;
    }

    setSubmitting(true);
    try {
      await api.createUser({
        email: form.email,
        employee_number: form.employeeNumber,
        password: form.password,
        full_name: form.fullName,
        role: "collection_point_staff",
        collection_point_id: Number(form.collectionPointId),
      });
      setSuccess(`Staff account created for ${form.fullName}.`);
      setForm(emptyForm);
    } catch (err) {
      setError(extractErrorMessage(err, "Couldn't create that account — please check the fields and try again."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="mb-10 rounded-2xl border border-ink/10 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-bold text-ink">Add a staff member</h2>
      <p className="mt-1 text-sm text-ink/60">
        Creates a collection-point-staff account. They'll sign in to the collection app with the
        employee number and password set here.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 grid gap-5 sm:grid-cols-2">
        <label className="block">
          <span className="text-sm font-semibold text-ink">Full name</span>
          <input
            type="text"
            required
            value={form.fullName}
            onChange={(e) => setForm({ ...form, fullName: e.target.value })}
            className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </label>

        <label className="block">
          <span className="text-sm font-semibold text-ink">Email</span>
          <input
            type="email"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </label>

        <label className="block">
          <span className="text-sm font-semibold text-ink">Employee number</span>
          <input
            type="text"
            inputMode="numeric"
            pattern="\d*"
            maxLength={EMPLOYEE_NUMBER_LENGTH}
            required
            placeholder={`${EMPLOYEE_NUMBER_LENGTH} digits`}
            value={form.employeeNumber}
            onChange={(e) =>
              setForm({ ...form, employeeNumber: keepDigits(e.target.value).slice(0, EMPLOYEE_NUMBER_LENGTH) })
            }
            className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </label>

        <label className="block">
          <span className="text-sm font-semibold text-ink">Branch</span>
          <select
            required
            value={form.collectionPointId}
            onChange={(e) => setForm({ ...form, collectionPointId: e.target.value })}
            className="mt-1.5 block w-full rounded-xl border border-ink/15 bg-white px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          >
            <option value="" disabled>
              Select a branch
            </option>
            {points.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-sm font-semibold text-ink">Password</span>
          <input
            type="password"
            required
            autoComplete="new-password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </label>

        <label className="block">
          <span className="text-sm font-semibold text-ink">Confirm password</span>
          <input
            type="password"
            required
            autoComplete="new-password"
            value={form.confirmPassword}
            onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
            className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
          {form.confirmPassword.length > 0 && !passwordsMatch && (
            <span className="mt-1 block text-xs font-medium text-red-600">Passwords don't match</span>
          )}
        </label>

        <ul className="sm:col-span-2 grid grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-2">
          {PASSWORD_RULES.map((rule) => {
            const met = rule.test(form.password);
            return (
              <li
                key={rule.label}
                className={`flex items-center gap-2 text-sm ${met ? "text-primary" : "text-ink/45"}`}
              >
                <span aria-hidden>{met ? "✓" : "○"}</span>
                {rule.label}
              </li>
            );
          })}
        </ul>

        {error && <p className="sm:col-span-2 text-sm font-medium text-red-600">{error}</p>}
        {success && <p className="sm:col-span-2 text-sm font-medium text-primary">{success}</p>}

        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-xl bg-forest px-6 py-2.5 font-bold text-white transition hover:bg-primary disabled:opacity-60"
          >
            {submitting ? "Creating…" : "Create staff account"}
          </button>
        </div>
      </form>
    </section>
  );
}
