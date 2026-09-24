// Shared by every authenticated app (collection-app, admin-portal): session
// handling where the refresh token persists in localStorage (survives a
// reload/reopen) and the access token stays in memory only. On load, a
// stored refresh token is exchanged for a fresh access token + the user's
// identity — the same rotation the backend already enforces (§14/ADR-04), so
// no app has to special-case "am I still logged in."
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { ApiError, createApiClient } from "@takaflow/api-client";
import type { UserOut } from "@takaflow/types";

const REFRESH_TOKEN_KEY = "takaflow_refresh_token";

export const api = createApiClient();

interface AuthState {
  user: UserOut | null;
  loading: boolean;
  error: string | null;
  login: (identifier: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!storedRefreshToken) {
      setLoading(false);
      return;
    }

    api
      .refresh(storedRefreshToken)
      .then(async (tokens) => {
        localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
        api.setAccessToken(tokens.access_token);
        setUser(await api.me());
      })
      .catch(() => {
        localStorage.removeItem(REFRESH_TOKEN_KEY);
      })
      .finally(() => setLoading(false));
  }, []);

  async function login(identifier: string, password: string) {
    setError(null);
    try {
      const tokens = await api.login(identifier, password);
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
      api.setAccessToken(tokens.access_token);
      setUser(await api.me());
    } catch (err) {
      setError(err instanceof ApiError ? String((err.detail as { detail?: string })?.detail ?? "Login failed") : "Login failed");
      throw err;
    }
  }

  function logout() {
    const storedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    api.setAccessToken(undefined);
    setUser(null);
    if (storedRefreshToken) {
      api.logout(storedRefreshToken).catch(() => {
        // Best-effort - the token is already discarded client-side either way.
      });
    }
  }

  return <AuthContext.Provider value={{ user, loading, error, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
