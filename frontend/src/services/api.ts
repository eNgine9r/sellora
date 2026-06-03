import { API_BASE_URL, authStorage, refreshAccessToken } from "@/services/auth.service";

let isRefreshing = false;

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown, message = `Sellora API request failed: ${status}`) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function redirectToLogin() {
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    window.location.assign("/login");
  }
}

function headersWithAuth(initHeaders: HeadersInit | undefined, body: BodyInit | null | undefined): HeadersInit {
  const headers: Record<string, string> = body instanceof FormData ? {} : { "Content-Type": "application/json" };
  const accessToken = authStorage.getAccessToken();
  const workspaceId = authStorage.getCurrentWorkspaceId();
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  if (workspaceId) headers["X-Workspace-ID"] = workspaceId;
  return { ...headers, ...Object.fromEntries(new Headers(initHeaders).entries()) };
}

export async function authenticatedFetch(path: string, init?: RequestInit, retry = true): Promise<Response> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: headersWithAuth(init?.headers, init?.body),
  });

  if (response.status !== 401 || !retry) {
    return response;
  }

  const refreshToken = authStorage.getRefreshToken();
  if (!refreshToken || isRefreshing) {
    authStorage.clear();
    redirectToLogin();
    return response;
  }

  try {
    isRefreshing = true;
    const tokens = await refreshAccessToken(refreshToken);
    authStorage.setTokens(tokens);
    return authenticatedFetch(path, init, false);
  } catch {
    authStorage.clear();
    redirectToLogin();
    return response;
  } finally {
    isRefreshing = false;
  }
}

async function readSafeErrorDetail(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return null;
  }

  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await authenticatedFetch(path, init);

  if (!response.ok) {
    const detail = await readSafeErrorDetail(response);
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
