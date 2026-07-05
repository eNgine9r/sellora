import { normalizeWorkspaceId } from "@/lib/workspace";
import { CurrentUser, TokenPair, WorkspaceMembership } from "@/types/auth";

const DEV_API_BASE_URL = "http://localhost:8000/api/v1";
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? (process.env.NODE_ENV === "production" ? "/api/v1" : DEV_API_BASE_URL);

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

const ACCESS_TOKEN_KEY = "sellora.access_token";
const REFRESH_TOKEN_KEY = "sellora.refresh_token";
const CURRENT_USER_KEY = "sellora.current_user";
const CURRENT_WORKSPACE_ID_KEY = "sellora.current_workspace_id";
function isBrowser() {
  return typeof window !== "undefined";
}

export const authStorage = {
  getAccessToken() {
    return isBrowser() ? window.localStorage.getItem(ACCESS_TOKEN_KEY) : null;
  },
  getRefreshToken() {
    return isBrowser() ? window.localStorage.getItem(REFRESH_TOKEN_KEY) : null;
  },
  getCurrentUser(): CurrentUser | null {
    if (!isBrowser()) return null;
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
  setTokens(tokens: TokenPair) {
    if (!isBrowser()) return;
    window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
    window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  },
  setCurrentUser(user: CurrentUser) {
    if (!isBrowser()) return;
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
    if (!isBrowser()) return;
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
    window.localStorage.removeItem(CURRENT_USER_KEY);
    window.localStorage.removeItem(CURRENT_WORKSPACE_ID_KEY);
  },
};

export async function loginWithPassword(email: string, password: string): Promise<TokenPair> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  } catch {
    throw new AuthNetworkError();
  }
  if (!response.ok) {
    throw new InvalidCredentialsError();
  }
  return response.json() as Promise<TokenPair>;
}

export async function refreshAccessToken(refreshToken: string): Promise<TokenPair> {
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
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
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
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
