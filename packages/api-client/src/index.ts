// Thin typed fetch client shared by every frontend app.
// Grows alongside backend routers — see docs/architecture-blueprint.html §14.

import type {
  AcceptedMaterialOut,
  CollectionPointOut,
  CollectionTransactionCreate,
  CollectionTransactionOut,
  InventorySaleCreate,
  InventorySaleOut,
  InventorySummaryOut,
  PaymentCreate,
  PaymentOut,
  ReportsSummaryOut,
  SyncBatchResponse,
  TokenResponse,
  UserCreate,
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

    login: (identifier: string, password: string) =>
      request<TokenResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ identifier, password }),
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

    createUser: (data: UserCreate) =>
      request<UserOut>("/auth/users", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    listAcceptedMaterials: (collectionPointId: number) =>
      request<AcceptedMaterialOut[]>(`/collection-points/${collectionPointId}/materials`),

    syncCollectionTransactions: (items: CollectionTransactionCreate[]) =>
      request<SyncBatchResponse>("/sync/collection-transactions", {
        method: "POST",
        body: JSON.stringify({ items }),
      }),

    listCollectionPoints: () => request<CollectionPointOut[]>("/collection-points"),

    listInventorySummary: (collectionPointId?: number) =>
      request<InventorySummaryOut[]>(
        `/inventory/summary${collectionPointId !== undefined ? `?collection_point_id=${collectionPointId}` : ""}`
      ),

    listCollectionTransactions: (params: { collectionPointId?: number; onDate?: string } = {}) => {
      const query = new URLSearchParams();
      if (params.collectionPointId !== undefined) query.set("collection_point_id", String(params.collectionPointId));
      if (params.onDate) query.set("on_date", params.onDate);
      const qs = query.toString();
      return request<CollectionTransactionOut[]>(`/collection-transactions${qs ? `?${qs}` : ""}`);
    },

    recordPayment: (transactionId: number, data: PaymentCreate) =>
      request<PaymentOut>(`/collection-transactions/${transactionId}/payments`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    listPayments: (transactionId: number) =>
      request<PaymentOut[]>(`/collection-transactions/${transactionId}/payments`),

    recordInventorySale: (data: InventorySaleCreate) =>
      request<InventorySaleOut>("/inventory/sales", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    listInventorySales: (collectionPointId?: number) =>
      request<InventorySaleOut[]>(
        `/inventory/sales${collectionPointId !== undefined ? `?collection_point_id=${collectionPointId}` : ""}`
      ),

    getReportsSummary: (params: { fromDate: string; toDate: string; collectionPointId?: number }) => {
      const query = new URLSearchParams({ from_date: params.fromDate, to_date: params.toDate });
      if (params.collectionPointId !== undefined) query.set("collection_point_id", String(params.collectionPointId));
      return request<ReportsSummaryOut>(`/reports/summary?${query.toString()}`);
    },

    // Phase 12: no auth required - the public site's data source (§05).
    listPublicCollectionPoints: () => request<CollectionPointOut[]>("/public/collection-points"),

    listPublicAcceptedMaterials: (collectionPointId: number) =>
      request<AcceptedMaterialOut[]>(`/public/collection-points/${collectionPointId}/materials`),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
