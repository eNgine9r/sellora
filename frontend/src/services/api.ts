import { normalizeWorkspaceId } from "@/lib/workspace";
import { API_BASE_URL, authStorage, refreshAccessToken } from "@/services/auth.service";

let isRefreshing = false;

export type ApiFieldError = {
  field: string;
  message: string;
};

export class ApiError extends Error {
  status: number;
  detail: unknown;
  path: string;
  fieldErrors: ApiFieldError[];

  constructor(status: number, detail: unknown, path: string, message = `Sellora API request failed: ${status}`) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.path = path;
    this.fieldErrors = extractFieldErrors(detail);
  }
}

function extractFieldErrors(detail: unknown): ApiFieldError[] {
  if (!detail || typeof detail !== "object" || !("detail" in detail)) return [];
  const errors = (detail as { detail?: unknown }).detail;
  if (!Array.isArray(errors)) return [];
  return errors.flatMap((error) => {
    if (!error || typeof error !== "object") return [];
    const loc = Array.isArray((error as { loc?: unknown }).loc) ? (error as { loc: unknown[] }).loc : [];
    const message = typeof (error as { msg?: unknown }).msg === "string" ? (error as { msg: string }).msg : "Invalid value";
    const field = loc.filter((part) => typeof part === "string" || typeof part === "number").join(".");
    return field ? [{ field, message }] : [];
  });
}

function safeEndpointPath(path: string): string {
  return path.split("?")[0].replace(/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/gi, ":id");
}

export function safeApiErrorMessage(error: unknown, fallback = "Unable to complete request. Please try again."): string {
  if (!(error instanceof ApiError)) return fallback;
  const endpoint = safeEndpointPath(error.path);
  const firstFieldError = error.fieldErrors[0];
  if (firstFieldError?.field.toLowerCase() === "header.x-workspace-id") {
    return "Workspace session is invalid. Please log in again.";
  }
  if (firstFieldError) {
    return `Request failed (${error.status}) on ${endpoint}. Field '${firstFieldError.field}' ${firstFieldError.message}.`;
  }
  if (error.status === 401) return "Session expired. Please log in again.";
  if (error.status === 403) return "You do not have permission for this action.";
  if (error.status === 404) return "Record not found.";
  if (error.status === 422) return `Invalid request for ${endpoint}. Please check the form or filters.`;
  if (error.status >= 500) return "Server error. Please try again later.";
  return `${fallback} (${error.status} on ${endpoint}).`;
}

function redirectToLogin() {
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    window.location.assign("/login");
  }
}

const WORKSPACE_HEADER = "X-Workspace-ID";

function workspaceSessionError(path: string): ApiError {
  return new ApiError(
    400,
    { detail: [{ loc: ["header", WORKSPACE_HEADER], msg: "Workspace session is invalid. Please log in again." }] },
    path,
  );
}

function headersWithAuth(path: string, initHeaders: HeadersInit | undefined, body: BodyInit | null | undefined): HeadersInit {
  const headers = new Headers(initHeaders);
  const explicitWorkspaceId = normalizeWorkspaceId(headers.get(WORKSPACE_HEADER));
  const explicitAuthorization = headers.get("Authorization");
  headers.delete(WORKSPACE_HEADER);
  headers.delete("Authorization");

  if (!(body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const accessToken = authStorage.getAccessToken();
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  } else if (explicitAuthorization) {
    headers.set("Authorization", explicitAuthorization);
  }

  const workspaceId = normalizeWorkspaceId(authStorage.getCurrentWorkspaceId()) ?? explicitWorkspaceId;
  const workspaceOptional = path === "/workspaces" || path === "/workspaces/";
  if (!workspaceId && !workspaceOptional) {
    throw workspaceSessionError(path);
  }
  if (workspaceId) {
    headers.set(WORKSPACE_HEADER, workspaceId);
  }
  return headers;
}

export async function authenticatedFetch(path: string, init?: RequestInit, retry = true): Promise<Response> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: headersWithAuth(path, init?.headers, init?.body),
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
    throw new ApiError(response.status, detail, path);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
