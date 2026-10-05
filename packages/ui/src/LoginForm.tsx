import { useEffect, useState, type FormEvent } from "react";
import { api, useAuth } from "./auth";
import { EMPLOYEE_NUMBER_LENGTH, isValidEmail, isValidEmployeeNumber, keepDigits } from "./validation";
import { EyeIcon } from "./icons";

export interface LoginFormProps {
  /** Small bold label above "Welcome back", e.g. "Collection Point System". */
  eyebrow: string;
  /** One line under "Welcome back" explaining what this app is for. */
  subtitle: string;
  /** Bottom-left label on the form panel, e.g. "TAKAFLOW POS · v1.0". */
  footerLabel: string;
  /** One line of copy over the photo, under the big "Turning Waste Into Worth." headline. */
  photoCaption: string;
  photoSrc: string;
  photoAlt: string;
  /**
   * "credentials" (default): email field, for the admin-portal — admins sign
   * in with email only. "employeeNumber": digit-only, exactly
   * EMPLOYEE_NUMBER_LENGTH characters, for the collection-app.
   */
  identifierMode?: "credentials" | "employeeNumber";
}

/** Live, not decorative — a real ping against /health, since a fake "System
 * operational" dot would be exactly the kind of unverifiable claim we just
 * cut everywhere else on this login screen. */
function SystemStatus() {
  const [status, setStatus] = useState<"checking" | "up" | "down">("checking");

  useEffect(() => {
    let cancelled = false;
    api
      .health()
      .then(() => !cancelled && setStatus("up"))
      .catch(() => !cancelled && setStatus("down"));
    return () => {
      cancelled = true;
    };
  }, []);

  const label = status === "checking" ? "Checking system…" : status === "up" ? "System operational" : "Can't reach server";
  const dot = status === "up" ? "bg-primary" : status === "down" ? "bg-red-500" : "bg-ink/30";

  return (
    <span className="flex items-center gap-1.5 text-xs font-medium text-ink/50">
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  );
}

export function LoginForm({
  eyebrow,
  subtitle,
  footerLabel,
  photoCaption,
  photoSrc,
  photoAlt,
  identifierMode = "credentials",
}: LoginFormProps) {
  const { login, error } = useAuth();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [clientError, setClientError] = useState<string | null>(null);

  const isEmployeeNumber = identifierMode === "employeeNumber";
  const identifierLabel = isEmployeeNumber ? "employee number" : "email";

  function handleIdentifierChange(value: string) {
    if (isEmployeeNumber) {
      const digitsOnly = keepDigits(value);
      // The user typed something that got filtered out — say so, instead of
      // the field just silently refusing to change (the bug being fixed here).
      setClientError(digitsOnly !== value ? "Employee number can only contain numbers (0–9)." : null);
      setIdentifier(digitsOnly.slice(0, EMPLOYEE_NUMBER_LENGTH));
    } else {
      setClientError(null);
      setIdentifier(value);
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setClientError(null);

    if (identifier.trim() === "") {
      setClientError(`Please enter your ${identifierLabel}.`);
      return;
    }
    if (isEmployeeNumber && !isValidEmployeeNumber(identifier)) {
      setClientError(`Employee number must be exactly ${EMPLOYEE_NUMBER_LENGTH} digits.`);
      return;
    }
    if (!isEmployeeNumber && !isValidEmail(identifier)) {
      setClientError("Please enter a valid email address.");
      return;
    }
    if (password === "") {
      setClientError("Please enter your password.");
      return;
    }

    setSubmitting(true);
    try {
      await login(identifier, password);
    } catch {
      // error is surfaced via useAuth().error
    } finally {
      setSubmitting(false);
    }
  }

  // The backend deliberately doesn't say which of identifier/password was
  // wrong (that would let someone probe for valid employee numbers) - this
  // just rephrases that same generic response in terms of this form's field.
  const wrongCredentials =
    error === "Invalid credentials" ? `Incorrect ${identifierLabel} or password.` : error;
  const displayError = clientError ?? wrongCredentials;

  return (
    <main className="flex min-h-screen items-center justify-center bg-mist/30 p-4 sm:p-8">
      <div className="grid w-full max-w-5xl overflow-hidden rounded-[2rem] bg-white shadow-2xl shadow-ink/10 lg:grid-cols-2">
        {/* Form panel */}
        <div className="flex flex-col justify-between gap-10 p-8 sm:p-12">
          <div className="flex items-center gap-2.5">
            <img src="/logo-mark.jpg" alt="TAKAFLOW" className="h-10 w-10 rounded-xl object-cover" />
            <span className="text-lg font-extrabold tracking-tight text-ink">TAKAFLOW</span>
          </div>

          <div>
            <span className="text-sm font-bold uppercase tracking-wider text-primary">{eyebrow}</span>
            <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-ink">Welcome back</h1>
            <p className="mt-3 leading-relaxed text-ink/60">{subtitle}</p>

            <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-5">
              <label className="block">
                <span className="text-sm font-semibold text-ink">
                  {isEmployeeNumber ? "Employee number" : "Email"}
                </span>
                <input
                  type={isEmployeeNumber ? "text" : "email"}
                  inputMode={isEmployeeNumber ? "numeric" : "email"}
                  pattern={isEmployeeNumber ? "\\d*" : undefined}
                  maxLength={isEmployeeNumber ? EMPLOYEE_NUMBER_LENGTH : undefined}
                  value={identifier}
                  onChange={(e) => handleIdentifierChange(e.target.value)}
                  autoComplete={isEmployeeNumber ? "off" : "email"}
                  placeholder={
                    isEmployeeNumber
                      ? `Enter your ${EMPLOYEE_NUMBER_LENGTH}-digit employee number`
                      : "Enter your email address"
                  }
                  className="mt-1.5 block w-full rounded-xl border border-ink/15 px-4 py-3 text-ink placeholder:text-ink/35 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
                />
              </label>

              <label className="block">
                <span className="text-sm font-semibold text-ink">Password</span>
                <div className="relative mt-1.5">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    placeholder="Enter your password"
                    className="block w-full rounded-xl border border-ink/15 px-4 py-3 pr-11 text-ink placeholder:text-ink/35 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
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

              {displayError && <p className="text-sm font-medium text-red-600">{displayError}</p>}

              <button
                type="submit"
                disabled={submitting}
                className="mt-2 flex items-center justify-center gap-2 rounded-xl bg-forest py-3.5 font-bold text-white transition hover:bg-primary disabled:opacity-60"
              >
                {submitting ? "Signing in…" : "Sign In"}
                {!submitting && <span aria-hidden>→</span>}
              </button>
            </form>
          </div>

          <div className="flex items-center justify-between text-xs text-ink/50">
            <span>{footerLabel}</span>
            <SystemStatus />
          </div>
        </div>

        {/* Photo panel */}
        <div className="relative hidden lg:block">
          <img src={photoSrc} alt={photoAlt} className="absolute inset-0 h-full w-full object-cover" />
          <div className="absolute inset-0 bg-forest/35" />
          <div className="absolute inset-x-0 bottom-0 p-10">
            <h2 className="text-4xl font-extrabold leading-tight text-white [text-shadow:0_2px_16px_rgb(0_0_0_/_45%)]">
              Turning Waste
              <br />
              Into Worth.
            </h2>
            <p className="mt-4 max-w-sm leading-relaxed text-white/85 [text-shadow:0_1px_10px_rgb(0_0_0_/_40%)]">
              {photoCaption}
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
