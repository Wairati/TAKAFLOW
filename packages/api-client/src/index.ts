// Thin typed fetch client shared by every frontend app.
// Grows alongside backend routers — see docs/architecture-blueprint.html §14.

import type {
  AcceptedMaterialOut,
  BuyerOrderCreate,
  BuyerOrderOut,
  BuyerOrderPaymentCreate,
  BuyerOrderPaymentOut,
  BuyerOrderStatus,
  CollectionPointOut,
  CollectionTransactionCreate,
  CollectionTransactionOut,
  InventorySummaryOut,
  MaterialOut,
  MaterialUpdate,
  PartnerCreate,
  PartnerOut,
  PartnerUpdate,
  PaymentCreate,
  PaymentOut,
  ReportsByBranchOut,
  ReportsSummaryOut,
  ReportsTimeseriesOut,
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
  // Registered by AuthProvider: exchanges the stored refresh token for a new
  // access token (returning it), or undefined if the refresh itself failed.
  let onUnauthorized: (() => Promise<string | undefined>) | undefined;

  async function request<T>(path: string, init?: RequestInit, isRetry = false): Promise<T> {
    const hadAuthHeader = Boolean(accessToken);
    const response = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...init?.headers,
      },
    });

    // A 15-minute access token routinely expires mid-session (e.g. midway
    // through filling out a form) - transparently refresh and retry once
    // rather than surfacing "Could not validate credentials" to the user.
    // Never applies to the login/refresh calls themselves (no auth header
    // on those to begin with), and never retries more than once.
    if (response.status === 401 && hadAuthHeader && !isRetry && onUnauthorized) {
      const newToken = await onUnauthorized();
      if (newToken) {
        accessToken = newToken;
        return request<T>(path, init, true);
      }
    }

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
    setUnauthorizedHandler(handler: (() => Promise<string | undefined>) | undefined) {
      onUnauthorized = handler;
    },

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

    listUsers: (params: { role?: string; collectionPointId?: number } = {}) => {
      const query = new URLSearchParams();
      if (params.role) query.set("role", params.role);
      if (params.collectionPointId !== undefined) query.set("collection_point_id", String(params.collectionPointId));
      const qs = query.toString();
      return request<UserOut[]>(`/auth/users${qs ? `?${qs}` : ""}`);
    },

    deactivateUser: (userId: number) =>
      request<UserOut>(`/auth/users/${userId}/deactivate`, { method: "POST" }),

    reactivateUser: (userId: number) =>
      request<UserOut>(`/auth/users/${userId}/reactivate`, { method: "POST" }),

    resetUserPassword: (userId: number, newPassword: string) =>
      request<UserOut>(`/auth/users/${userId}/reset-password`, {
        method: "POST",
        body: JSON.stringify({ new_password: newPassword }),
      }),

    listAcceptedMaterials: (collectionPointId: number) =>
      request<AcceptedMaterialOut[]>(`/collection-points/${collectionPointId}/materials`),

    listMaterials: (isActive?: boolean) =>
      request<MaterialOut[]>(`/materials${isActive !== undefined ? `?is_active=${isActive}` : ""}`),

    updateMaterial: (materialId: number, data: MaterialUpdate) =>
      request<MaterialOut>(`/materials/${materialId}`, { method: "PATCH", body: JSON.stringify(data) }),

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

    getReportsSummary: (params: { fromDate: string; toDate: string; collectionPointId?: number }) => {
      const query = new URLSearchParams({ from_date: params.fromDate, to_date: params.toDate });
      if (params.collectionPointId !== undefined) query.set("collection_point_id", String(params.collectionPointId));
      return request<ReportsSummaryOut>(`/reports/summary?${query.toString()}`);
    },

    getReportsTimeseries: (params: { fromDate: string; toDate: string; collectionPointId?: number }) => {
      const query = new URLSearchParams({ from_date: params.fromDate, to_date: params.toDate });
      if (params.collectionPointId !== undefined) query.set("collection_point_id", String(params.collectionPointId));
      return request<ReportsTimeseriesOut>(`/reports/timeseries?${query.toString()}`);
    },

    getReportsByBranch: (params: { fromDate: string; toDate: string }) => {
      const query = new URLSearchParams({ from_date: params.fromDate, to_date: params.toDate });
      return request<ReportsByBranchOut>(`/reports/by-branch?${query.toString()}`);
    },

    // Phase 12: no auth required - the public site's data source (§05).
    listPublicCollectionPoints: () => request<CollectionPointOut[]>("/public/collection-points"),

    listPublicAcceptedMaterials: (collectionPointId: number) =>
      request<AcceptedMaterialOut[]>(`/public/collection-points/${collectionPointId}/materials`),

    // ---- Partners (collaborative collections) -------------------------

    listPartners: (isActive?: boolean) =>
      request<PartnerOut[]>(`/partners${isActive !== undefined ? `?is_active=${isActive}` : ""}`),

    createPartner: (data: PartnerCreate) =>
      request<PartnerOut>("/partners", { method: "POST", body: JSON.stringify(data) }),

    updatePartner: (partnerId: number, data: PartnerUpdate) =>
      request<PartnerOut>(`/partners/${partnerId}`, { method: "PATCH", body: JSON.stringify(data) }),

    // ---- Buyer orders ---------------------------------------------------

    createBuyerOrder: (data: BuyerOrderCreate) =>
      request<BuyerOrderOut>("/buyer-orders", { method: "POST", body: JSON.stringify(data) }),

    listBuyerOrders: (status?: BuyerOrderStatus) =>
      request<BuyerOrderOut[]>(`/buyer-orders${status ? `?status=${status}` : ""}`),

    getBuyerOrder: (orderId: number) => request<BuyerOrderOut>(`/buyer-orders/${orderId}`),

    cancelBuyerOrder: (orderId: number) =>
      request<BuyerOrderOut>(`/buyer-orders/${orderId}/cancel`, { method: "POST" }),

    recordBuyerOrderPayment: (orderId: number, data: BuyerOrderPaymentCreate) =>
      request<BuyerOrderPaymentOut>(`/buyer-orders/${orderId}/payments`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    listBuyerOrderPayments: (orderId: number) =>
      request<BuyerOrderPaymentOut[]>(`/buyer-orders/${orderId}/payments`),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
