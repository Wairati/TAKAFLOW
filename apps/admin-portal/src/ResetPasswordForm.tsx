// The actual answer to "someone forgot their password" for a staff account:
// an admin sets a new one here. Calls the same reset-password endpoint the
// backend's reset_password.py script uses for the one case this form can't
// cover — an admin locked out of their own account with no one else to ask.
import { useState, type FormEvent } from "react";
import { api, PASSWORD_RULES, isPasswordValid, EyeIcon } from "@takaflow/ui";
import { ApiError } from "@takaflow/api-client";
import type { UserOut } from "@takaflow/types";

function extractErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    const detail = (err.detail as { detail?: unknown })?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

export function ResetPasswordForm({
  user,
  onDone,
  onCancel,
}: {
  user: UserOut;
  onDone: () => void;
  onCancel: () => void;
}) {
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const passwordsMatch = password.length > 0 && password === confirmPassword;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (password === "") {
      setError("Please enter a new password.");
      return;
    }
    if (!isPasswordValid(password)) {
      setError("Password doesn't meet all the requirements below.");
      return;
    }
    if (confirmPassword === "") {
      setError("Please confirm the new password.");
      return;
    }
    if (!passwordsMatch) {
      setError("Passwords don't match.");
      return;
    }

    setSubmitting(true);
    try {
      await api.resetUserPassword(user.id, password);
      onDone();
    } catch (err) {
      setError(extractErrorMessage(err, "Couldn't reset that password — try again."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-xl bg-mint/20 p-4">
      <p className="text-sm font-bold text-ink">New password for {user.full_name}</p>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block">
          <span className="text-xs font-semibold text-ink/70">New password</span>
          <div className="relative mt-1">
            <input
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="block w-full rounded-lg border border-ink/15 px-3 py-2 pr-9 text-sm outline-none focus:border-primary"
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink/40 hover:text-ink/70"
            >
              <EyeIcon open={showPassword} className="h-4 w-4" />
            </button>
          </div>
        </label>
        <label className="block">
          <span className="text-xs font-semibold text-ink/70">Confirm password</span>
          <input
            type={showPassword ? "text" : "password"}
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="mt-1 block w-full rounded-lg border border-ink/15 px-3 py-2 text-sm outline-none focus:border-primary"
          />
        </label>
      </div>

      <ul className="grid grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-2">
        {PASSWORD_RULES.map((rule) => {
          const met = rule.test(password);
          return (
            <li key={rule.label} className={`flex items-center gap-2 text-xs ${met ? "text-primary" : "text-ink/45"}`}>
              <span aria-hidden>{met ? "✓" : "○"}</span>
              {rule.label}
            </li>
          );
        })}
      </ul>

      {error && <p className="text-xs font-medium text-red-600">{error}</p>}

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-lg bg-forest px-3.5 py-1.5 text-xs font-bold text-white transition hover:bg-primary disabled:opacity-60"
        >
          {submitting ? "Setting…" : "Set new password"}
        </button>
        <button type="button" onClick={onCancel} className="text-xs font-semibold text-ink/50">
          Cancel
        </button>
      </div>
    </form>
  );
}
