import { normalizeWorkspaceId } from "@/lib/workspace";
import { CurrentUser, TokenPair, WorkspaceMembership } from "@/types/auth";

export const COOKIE_SESSION_AUTH_ENABLED = process.env.NEXT_PUBLIC_COOKIE_SESSION_AUTH_ENABLED === "true";
let memoryAccessToken: string | null = null;
let refreshInFlight: Promise<TokenPair> | null = null;

const DEV_API_BASE_URL = "http://localhost:8000/api/v1";
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? (process.env.NODE_ENV === "production" ? "/api/v1" : DEV_API_BASE_URL);

const DEFAULT_AUTH_REQUEST_TIMEOUT_MS = 12_000;
const configuredAuthTimeout = Number(process.env.NEXT_PUBLIC_API_TIMEOUT_MS ?? DEFAULT_AUTH_REQUEST_TIMEOUT_MS);
export const AUTH_REQUEST_TIMEOUT_MS = Number.isFinite(configuredAuthTimeout) && configuredAuthTimeout >= 1_000
  ? configuredAuthTimeout
  : DEFAULT_AUTH_REQUEST_TIMEOUT_MS;

export class AuthNetworkError extends Error {
  constructor() {
    super("AUTH_NETWORK_UNAVAILABLE");
    this.name = "AuthNetworkError";
  }
}

export class InvalidCredentialsError extends Error {
  constructor() {
    super("AUTH_INVALID_CREDENTIALS");
    this.name = "InvalidCredentialsError";
  }
}

export class SecureSessionExpiredError extends Error {
  constructor() {
    super("SECURE_SESSION_EXPIRED");
    this.name = "SecureSessionExpiredError";
  }
}

export class AuthRateLimitedError extends Error {
  readonly retryAfterSeconds: number;

  constructor(retryAfterSeconds: number) {
    super("AUTH_RATE_LIMITED");
    this.name = "AuthRateLimitedError";
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

const ACCESS_TOKEN_KEY = "sellora.access_token";
const REFRESH_TOKEN_KEY = "sellora.refresh_token";
const CURRENT_USER_KEY = "sellora.current_user";
const CURRENT_WORKSPACE_ID_KEY = "sellora.current_workspace_id";
function isBrowser() {
  return typeof window !== "undefined";
}

async function fetchWithAuthTimeout(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), AUTH_REQUEST_TIMEOUT_MS);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch {
    throw new AuthNetworkError();
  } finally {
    clearTimeout(timeoutId);
  }
}

export const authStorage = {
  getAccessToken() {
    return COOKIE_SESSION_AUTH_ENABLED ? memoryAccessToken : (isBrowser() ? window.localStorage.getItem(ACCESS_TOKEN_KEY) : null);
  },
  getRefreshToken() {
    return COOKIE_SESSION_AUTH_ENABLED ? null : (isBrowser() ? window.localStorage.getItem(REFRESH_TOKEN_KEY) : null);
  },
  getCurrentUser(): CurrentUser | null {
    if (!isBrowser() || COOKIE_SESSION_AUTH_ENABLED) return null;
    const value = window.localStorage.getItem(CURRENT_USER_KEY);
    if (!value) return null;
    try {
      return JSON.parse(value) as CurrentUser;
    } catch {
      return null;
    }
  },
  getCurrentWorkspaceId() {
    if (!isBrowser()) return null;
    const workspaceId = normalizeWorkspaceId(window.localStorage.getItem(CURRENT_WORKSPACE_ID_KEY));
    if (!workspaceId) {
      window.localStorage.removeItem(CURRENT_WORKSPACE_ID_KEY);
      return null;
    }
    return workspaceId;
  },
  readLegacyTokens(): TokenPair | null {
    if (!isBrowser()) return null;
    const access_token = window.localStorage.getItem(ACCESS_TOKEN_KEY);
    const refresh_token = window.localStorage.getItem(REFRESH_TOKEN_KEY);
    return access_token && refresh_token ? { access_token, refresh_token, token_type: "bearer" } : null;
  },
  setTokens(tokens: TokenPair) {
    if (!isBrowser()) return;
    if (COOKIE_SESSION_AUTH_ENABLED) {
      memoryAccessToken = tokens.access_token;
      window.localStorage.removeItem(ACCESS_TOKEN_KEY);
      window.localStorage.removeItem(REFRESH_TOKEN_KEY);
      window.localStorage.removeItem(CURRENT_USER_KEY);
      return;
    }
    window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
    window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  },
  setCurrentUser(user: CurrentUser) {
    if (!isBrowser()) return;
    if (COOKIE_SESSION_AUTH_ENABLED) {
      window.localStorage.removeItem(CURRENT_USER_KEY);
      return;
    }
    window.localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(user));
  },
  setCurrentWorkspaceId(workspaceId: unknown) {
    if (!isBrowser()) return;
    const normalizedWorkspaceId = normalizeWorkspaceId(workspaceId);
    if (!normalizedWorkspaceId) {
      window.localStorage.removeItem(CURRENT_WORKSPACE_ID_KEY);
      return;
    }
    window.localStorage.setItem(CURRENT_WORKSPACE_ID_KEY, normalizedWorkspaceId);
  },
  clear() {
    memoryAccessToken = null;
    if (!isBrowser()) return;
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
    window.localStorage.removeItem(CURRENT_USER_KEY);
    window.localStorage.removeItem(CURRENT_WORKSPACE_ID_KEY);
  },
};

export async function loginWithPassword(email: string, password: string): Promise<TokenPair> {
  const path = COOKIE_SESSION_AUTH_ENABLED ? "/auth/session/login" : "/auth/login";
  const response = await fetchWithAuthTimeout(`${API_BASE_URL}${path}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    if (response.status === 429) {
      const seconds = Number(response.headers.get("Retry-After"));
      throw new AuthRateLimitedError(Number.isFinite(seconds) && seconds > 0 ? Math.ceil(seconds) : 900);
    }
    if (response.status === 401 || response.status === 422) {
      throw new InvalidCredentialsError();
    }
    throw new AuthNetworkError();
  }
  const result = await response.json() as TokenPair;
  return COOKIE_SESSION_AUTH_ENABLED
    ? { access_token: result.access_token, refresh_token: "", token_type: "bearer" }
    : result;
}

async function requestSessionRefresh(attempt = 0): Promise<TokenPair> {
  const response = await fetchWithAuthTimeout(`${API_BASE_URL}/auth/session/refresh`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
  });
  if (response.status === 409 && attempt === 0) {
    // Another tab rotated the cookie; allow its Set-Cookie response to settle.
    await new Promise((resolve) => setTimeout(resolve, 350));
    return requestSessionRefresh(1);
  }
  if (response.status === 401) throw new SecureSessionExpiredError();
  if (!response.ok) throw new AuthNetworkError();
  const result = await response.json() as { access_token: string };
  return { access_token: result.access_token, refresh_token: "", token_type: "bearer" };
}

export function refreshCookieSession(): Promise<TokenPair> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = requestSessionRefresh().finally(() => { refreshInFlight = null; });
  return refreshInFlight;
}

export async function upgradeLegacySession(accessToken: string): Promise<TokenPair> {
  const response = await fetchWithAuthTimeout(`${API_BASE_URL}/auth/session/upgrade`, {
    method: "POST",
    credentials: "same-origin",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) throw new Error("Legacy session migration failed");
  const data = await response.json() as { access_token: string };
  return { access_token: data.access_token, refresh_token: "", token_type: "bearer" };
}

export async function revokeCookieSession(): Promise<void> {
  const response = await fetchWithAuthTimeout(`${API_BASE_URL}/auth/session/logout`, {
    method: "POST",
    credentials: "same-origin",
  });
  if (!response.ok) throw new Error("Unable to revoke secure session");
}

export async function refreshLegacyAccessToken(refreshToken: string): Promise<TokenPair> {
  const response = await fetchWithAuthTimeout(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) throw new Error("Legacy session expired");
  return response.json() as Promise<TokenPair>;
}

export async function refreshAccessToken(refreshToken: string): Promise<TokenPair> {
  if (COOKIE_SESSION_AUTH_ENABLED) return refreshCookieSession();
  const response = await fetchWithAuthTimeout(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) {
    throw new Error("Unable to refresh session");
  }
  return response.json() as Promise<TokenPair>;
}

export async function fetchCurrentUser(accessToken: string): Promise<CurrentUser> {
  const response = await fetchWithAuthTimeout(`${API_BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    throw new Error("Unable to load current user");
  }
  return response.json() as Promise<CurrentUser>;
}

export function firstAvailableWorkspace(user: CurrentUser): WorkspaceMembership | null {
  return user.memberships.find((membership) => normalizeWorkspaceId(membership.workspace_id)) ?? null;
}
