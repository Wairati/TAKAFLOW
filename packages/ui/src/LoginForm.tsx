import { useState, type FormEvent } from "react";
import { useAuth } from "./auth";

export function LoginForm({ title }: { title: string }) {
  const { login, error } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await login(email, password);
    } catch {
      // error is surfaced via useAuth().error
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main style={{ fontFamily: "sans-serif", maxWidth: 360, margin: "4rem auto", padding: "0 1rem" }}>
      <h1 style={{ fontSize: "1.5rem" }}>{title}</h1>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{ display: "block", width: "100%", padding: "0.5rem" }}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ display: "block", width: "100%", padding: "0.5rem" }}
          />
        </label>
        {error && <p style={{ color: "crimson" }}>{error}</p>}
        <button type="submit" disabled={submitting} style={{ padding: "0.6rem" }}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </main>
  );
}
