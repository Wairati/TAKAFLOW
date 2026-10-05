// Admin-only: provisions a new collection-point-staff or admin account.
// There's no self-registration (accounts are provisioned, not signed up
// for), and the backend rejects this call outright for anyone who isn't an
// admin — this form just gives that existing POST /auth/users route a real
// screen.
import { useEffect, useState, type FormEvent } from "react";
import { ApiError } from "@takaflow/api-client";
import {
  api,
  EMPLOYEE_NUMBER_LENGTH,
  isValidEmployeeNumber,
  isValidEmail,
  keepDigits,
  PASSWORD_RULES,
  isPasswordValid,
  EyeIcon,
  fullNameError,
} from "@takaflow/ui";
import type { CollectionPointOut, UserRole } from "@takaflow/types";

function extractErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    const detail = (err.detail as { detail?: unknown })?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  }
  return fallback;
}

const emptyForm = {
  role: "collection_point_staff" as UserRole,
  fullName: "",
  email: "",
  employeeNumber: "",
  collectionPointId: "",
  password: "",
  confirmPassword: "",
};

export function CreateStaffForm({ onCreated }: { onCreated?: () => void }) {
  const [points, setPoints] = useState<CollectionPointOut[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  useEffect(() => {
    api.listCollectionPoints().then(setPoints).catch(() => setPoints([]));
  }, []);

  const passwordsMatch = form.password.length > 0 && form.password === form.confirmPassword;
  const isAdmin = form.role === "admin";

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (form.fullName.trim() === "") {
      setError(`Please enter the ${isAdmin ? "admin" : "staff member"}'s full name.`);
      return;
    }
    const nameError = fullNameError(form.fullName);
    if (nameError) {
      setError(nameError);
      return;
    }
    if (form.email.trim() === "") {
      setError("Please enter an email address.");
      return;
    }
    if (!isValidEmail(form.email)) {
      setError("Please enter a valid email address.");
      return;
    }
    if (!isAdmin) {
      if (form.employeeNumber === "") {
        setError("Please enter an employee number.");
        return;
      }
      if (!isValidEmployeeNumber(form.employeeNumber)) {
        setError(`Employee number must be exactly ${EMPLOYEE_NUMBER_LENGTH} digits.`);
        return;
      }
      if (!form.collectionPointId) {
        setError("Select a branch for this staff member.");
        return;
      }
    }
    if (form.password === "") {
      setError("Please enter a password.");
      return;
    }
    if (!isPasswordValid(form.password)) {
      setError("Password doesn't meet all the requirements below.");
      return;
    }
    if (form.confirmPassword === "") {
      setError("Please confirm the password.");
      return;
    }
    if (!passwordsMatch) {
      setError("Passwords don't match.");
      return;
    }

    setSubmitting(true);
    try {
      await api.createUser({
        email: form.email.trim(),
        employee_number: isAdmin ? null : form.employeeNumber,
        password: form.password,
        full_name: form.fullName.trim(),
        role: form.role,
        collection_point_id: isAdmin ? null : Number(form.collectionPointId),
      });
      setSuccess(`${isAdmin ? "Admin" : "Staff"} account created for ${form.fullName}.`);
      setForm(emptyForm);
      setShowPassword(false);
      setShowConfirmPassword(false);
      onCreated?.();
    } catch (err) {
      setError(extractErrorMessage(err, "Couldn't create that account — please check the fields and try again."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="rounded-2xl border border-ink/10 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-bold text-ink">Add a staff member or admin</h2>
      <p className="mt-1 text-sm text-ink/60">
        {isAdmin
          ? "Creates an admin account. They'll sign in to the admin portal with their email and the password set here."
          : "Creates a collection-point-staff account. They'll sign in to the collection app with the employee number and password set here."}
      </p>

      <form onSubmit={handleSubmit} className="mt-6 grid gap-5 sm:grid-cols-2">
        <div className="block sm:col-span-2">
          <span className="text-sm font-semibold text-ink">Account type</span>
          <div className="mt-1.5 inline-flex rounded-xl border border-ink/15 p-1">
            {(
              [
                { value: "collection_point_staff" as UserRole, label: "Collection point staff" },
                { value: "admin" as UserRole, label: "Admin" },
              ]
            ).map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setForm({ ...form, role: option.value })}
                className={`rounded-lg px-4 py-1.5 text-sm font-semibold transition ${
                  form.role === option.value ? "bg-forest text-white" : "text-ink/60 hover:bg-black/5"
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <label className="block">
          <span className="text-sm font-semibold text-ink">Full name</span>
          <input
            type="text"
            value={form.fullName}
            onChange={(e) => setForm({ ...form, fullName: e.target.value })}
            className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </label>

        <label className="block">
          <span className="text-sm font-semibold text-ink">Email</span>
          <input
            type="text"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </label>

        {!isAdmin && (
          <label className="block">
            <span className="text-sm font-semibold text-ink">Employee number</span>
            <input
              type="text"
              inputMode="numeric"
              pattern="\d*"
              maxLength={EMPLOYEE_NUMBER_LENGTH}
              placeholder={`${EMPLOYEE_NUMBER_LENGTH} digits`}
              value={form.employeeNumber}
              onChange={(e) =>
                setForm({ ...form, employeeNumber: keepDigits(e.target.value).slice(0, EMPLOYEE_NUMBER_LENGTH) })
              }
              className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </label>
        )}

        {!isAdmin && (
          <label className="block">
            <span className="text-sm font-semibold text-ink">Branch</span>
            <select
              value={form.collectionPointId}
              onChange={(e) => setForm({ ...form, collectionPointId: e.target.value })}
              className="mt-1.5 block w-full rounded-xl border border-ink/15 bg-white px-4 py-2.5 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            >
              <option value="">Select a branch</option>
              {points.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="block">
          <span className="text-sm font-semibold text-ink">Password</span>
          <div className="relative mt-1.5">
            <input
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="block w-full rounded-xl border border-ink/15 px-4 py-2.5 pr-11 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-ink/40 transition hover:text-ink/70"
            >
              <EyeIcon open={showPassword} className="h-5 w-5" />
            </button>
          </div>
        </label>

        <label className="block">
          <span className="text-sm font-semibold text-ink">Confirm password</span>
          <div className="relative mt-1.5">
            <input
              type={showConfirmPassword ? "text" : "password"}
              autoComplete="new-password"
              value={form.confirmPassword}
              onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
              className="block w-full rounded-xl border border-ink/15 px-4 py-2.5 pr-11 text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword((v) => !v)}
              aria-label={showConfirmPassword ? "Hide password" : "Show password"}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-ink/40 transition hover:text-ink/70"
            >
              <EyeIcon open={showConfirmPassword} className="h-5 w-5" />
            </button>
          </div>
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
            {submitting ? "Creating…" : isAdmin ? "Create admin account" : "Create staff account"}
          </button>
        </div>
      </form>
    </section>
  );
}
