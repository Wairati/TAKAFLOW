// Thin typed fetch client shared by every frontend app.
// Grows alongside backend routers — see docs/architecture-blueprint.html §14.

import type {
  AcceptedMaterialOut,
  CollectionTransactionCreate,
  SyncBatchResponse,
  TokenResponse,
  UserOut,
} from "@takaflow/types";

const DEFAULT_BASE_URL = "http://localhost:8000/api/v1";

export interface ApiClientOptions {
  baseUrl?: string;
  accessToken?: string;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(`API request failed: ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

export function createApiClient(options: ApiClientOptions = {}) {
  const baseUrl = options.baseUrl ?? DEFAULT_BASE_URL;
  let accessToken = options.accessToken;

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...init?.headers,
      },
    });

    if (!response.ok) {
      let detail: unknown;
      try {
        detail = await response.json();
      } catch {
        detail = await response.text();
      }
      throw new ApiError(response.status, detail);
    }

    if (response.status === 204) {
      return undefined as T;
    }
    return response.json() as Promise<T>;
  }

  return {
    setAccessToken(token: string | undefined) {
      accessToken = token;
    },

    health: () => request<{ status: string }>("/health"),

    login: (email: string, password: string) =>
      request<TokenResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),

    refresh: (refresh_token: string) =>
      request<TokenResponse>("/auth/refresh", {
        method: "POST",
        body: JSON.stringify({ refresh_token }),
      }),

    logout: (refresh_token: string) =>
      request<void>("/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token }),
      }),

    me: () => request<UserOut>("/auth/me"),

    listAcceptedMaterials: (collectionPointId: number) =>
      request<AcceptedMaterialOut[]>(`/collection-points/${collectionPointId}/materials`),

    syncCollectionTransactions: (items: CollectionTransactionCreate[]) =>
      request<SyncBatchResponse>("/sync/collection-transactions", {
        method: "POST",
        body: JSON.stringify({ items }),
      }),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
