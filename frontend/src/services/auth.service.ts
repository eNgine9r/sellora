import { normalizeWorkspaceId } from "@/lib/workspace";
import { CurrentUser, TokenPair, WorkspaceMembership } from "@/types/auth";

// Staging is intentionally running the revocable cookie-session pilot globally.
// The default host is exact, not a suffix match; non-staging domains retain
// existing legacy auth until their own controlled cutover.
function secureStagingHost(): boolean {
  if (typeof window === "undefined") return false;
  const hosts = (process.env.NEXT_PUBLIC_COOKIE_SESSION_STAGING_HOSTS ??
    "sellora-web-staging.vercel.app")
    .split(",")
    .map((host) => host.trim().toLowerCase())
    .filter(Boolean);
  return hosts.includes(window.location.hostname.toLowerCase());
}
export const COOKIE_SESSION_AUTH_ENABLED =
  process.env.NEXT_PUBLIC_COOKIE_SESSION_AUTH_ENABLED === "true" ||
  secureStagingHost();
let memoryAccessToken: string | null = null;
let memoryActorId: string | null = null;
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

async function consumeAuthResponse<T>(input: RequestInfo | URL, init: RequestInit | undefined, consume: (response: Response) => Promise<T>): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), AUTH_REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(input, { ...init, signal: controller.signal }).catch(() => { throw new AuthNetworkError(); });
    try {
      return await consume(response);
    } catch (error) {
      if (controller.signal.aborted) throw new AuthNetworkError();
      throw error;
    }
  } finally {
    clearTimeout(timeoutId);
  }
}

async function fetchWithAuthTimeout(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  return consumeAuthResponse(input, init, async response => response);
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
  getCurrentActorId(): string | null { return memoryActorId ?? this.getCurrentUser()?.id ?? null; },
  setCurrentUser(user: CurrentUser) {
    if (!isBrowser()) return;
    if (memoryActorId && memoryActorId !== user.id) {
      window.sessionStorage.removeItem("sellora.meta-ads.intent");
      Reflect.deleteProperty(window, "__selloraMetaAdsCallback");
    }
    memoryActorId = user.id;
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
    if (window.localStorage.getItem(CURRENT_WORKSPACE_ID_KEY) !== normalizedWorkspaceId) {
      window.sessionStorage.removeItem("sellora.meta-ads.intent");
      Reflect.deleteProperty(window, "__selloraMetaAdsCallback");
    }
    window.localStorage.setItem(CURRENT_WORKSPACE_ID_KEY, normalizedWorkspaceId);
  },
  clear() {
    memoryAccessToken = null;
    memoryActorId = null;
    if (!isBrowser()) return;
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
    window.localStorage.removeItem(CURRENT_USER_KEY);
    window.localStorage.removeItem(CURRENT_WORKSPACE_ID_KEY);
    window.sessionStorage.removeItem("sellora.meta-ads.intent");
    Reflect.deleteProperty(window, "__selloraMetaAdsCallback");
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
  // Bootstrap draining must be bounded through JSON consumption, not just headers.
  const { response, result } = await consumeAuthResponse(`${API_BASE_URL}/auth/session/refresh`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
  }, async response => ({ response, result: response.ok ? await response.json() : null }));
  if (response.status === 409 && attempt === 0) {
    // Another tab rotated the cookie; allow its Set-Cookie response to settle.
    await new Promise((resolve) => setTimeout(resolve, 350));
    return requestSessionRefresh(1);
  }
  if (response.status === 401) throw new SecureSessionExpiredError();
  if (!response.ok) throw new AuthNetworkError();
  return { access_token: (result as { access_token: string }).access_token, refresh_token: "", token_type: "bearer" };
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
  return consumeAuthResponse(`${API_BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  }, async response => {
    if (!response.ok) throw new Error("Unable to load current user");
    return response.json() as Promise<CurrentUser>;
  });
}

export function firstAvailableWorkspace(user: CurrentUser): WorkspaceMembership | null {
  return user.memberships.find((membership) => normalizeWorkspaceId(membership.workspace_id)) ?? null;
}

export type SignInProvider = "google" | "facebook";

export type PublicAuthOptions = {
  providers: SignInProvider[];
  signup_providers: SignInProvider[];
  email_registration: boolean;
  origin: string | null;
};

const EMPTY_AUTH_OPTIONS: PublicAuthOptions = {
  providers: [], signup_providers: [], email_registration: false, origin: null,
};
const PUBLIC_AUTH_PATH = "/auth/session/access";

export class PublicAuthError extends Error {
  constructor(readonly code: string) {
    super(code);
  }
}

async function publicAuthRequest<T>(path: string, body?: object, authenticated = false): Promise<T> {
  const headers: Record<string, string> = {};
  if (body) headers["Content-Type"] = "application/json";
  if (authenticated) {
    const token = authStorage.getAccessToken();
    if (!token) throw new PublicAuthError("session_required");
    headers.Authorization = `Bearer ${token}`;
  }
  return consumeAuthResponse(`${API_BASE_URL}${PUBLIC_AUTH_PATH}${path}`, {
    method: body ? "POST" : "GET", body: body ? JSON.stringify(body) : undefined,
    headers, credentials: "same-origin", cache: "no-store",
  }, async (response) => {
    if (!response.ok) {
      const result = await response.json().catch(() => null);
      throw new PublicAuthError(typeof result?.detail === "string" ? result.detail : "unavailable");
    }
    return (response.status === 204 ? undefined : await response.json()) as T;
  });
}

export async function fetchPublicAuthOptions(): Promise<PublicAuthOptions> {
  if (!COOKIE_SESSION_AUTH_ENABLED || !API_BASE_URL.startsWith("/")) return EMPTY_AUTH_OPTIONS;
  const options = await publicAuthRequest<PublicAuthOptions>("/options");
  return options.origin === window.location.origin ? options : EMPTY_AUTH_OPTIONS;
}

export async function startSocialAuth(provider: SignInProvider, intent: "login" | "register" | "link",
                                      locale: "uk" | "en", acceptsTerms = false): Promise<void> {
  const result = await publicAuthRequest<{ authorization_url: string }>(
    `/${provider}/start`, { intent, locale, accepts_terms: acceptsTerms }, intent === "link",
  );
  const url = new URL(result.authorization_url);
  const expectedHost = provider === "google" ? "accounts.google.com" : "www.facebook.com";
  if (url.protocol !== "https:" || url.host !== expectedHost || url.username || url.password) {
    throw new PublicAuthError("provider_error");
  }
  window.location.assign(url.href);
}

export function fetchLinkedSignInMethods() {
  return publicAuthRequest<{ linked: SignInProvider[] }>("/identities", undefined, true);
}

export function sendRegistrationCode(email: string, locale: "uk" | "en", social: boolean) {
  return publicAuthRequest<{ accepted: boolean }>("/email/send", { email, locale, social });
}

export function confirmRegistration(body: {
  email: string; code: string; locale: "uk" | "en"; social: boolean; first_name?: string; password?: string; accepts_terms?: boolean;
}) {
  return publicAuthRequest<void>("/email/confirm", body);
}
