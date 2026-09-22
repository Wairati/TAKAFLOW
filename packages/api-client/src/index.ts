// Thin typed fetch client shared by every frontend app.
// Grows alongside backend routers — see docs/architecture-blueprint.html §14.

const DEFAULT_BASE_URL = "http://localhost:8000/api/v1";

export interface ApiClientOptions {
  baseUrl?: string;
  accessToken?: string;
}

export function createApiClient(options: ApiClientOptions = {}) {
  const baseUrl = options.baseUrl ?? DEFAULT_BASE_URL;

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(options.accessToken ? { Authorization: `Bearer ${options.accessToken}` } : {}),
        ...init?.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }

    return response.json() as Promise<T>;
  }

  return {
    health: () => request<{ status: string }>("/health"),
  };
}
