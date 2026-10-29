"use client";

import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { normalizeWorkspaceId } from "@/lib/workspace";
import { COOKIE_SESSION_AUTH_ENABLED, authStorage, fetchCurrentUser, firstAvailableWorkspace, loginWithPassword, refreshAccessToken, refreshCookieSession, revokeCookieSession } from "@/services/auth.service";
import { CurrentUser, WorkspaceMembership } from "@/types/auth";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

type AuthContextValue = {
  status: AuthStatus;
  currentUser: CurrentUser | null;
  currentWorkspaceId: string | null;
  currentWorkspace: WorkspaceMembership | null;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  switchWorkspace: (workspaceId: string) => void;
  reloadCurrentUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const authGeneration = useRef(0);
  const bootstrapPending = useRef<Promise<void>>(Promise.resolve());
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [currentWorkspaceId, setCurrentWorkspaceId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const applyUser = useCallback((user: CurrentUser) => {
    const storedWorkspaceId = authStorage.getCurrentWorkspaceId();
    const selectedWorkspace = user.memberships.find((membership) => normalizeWorkspaceId(membership.workspace_id) === storedWorkspaceId) ?? firstAvailableWorkspace(user);
    const normalizedWorkspaceId = normalizeWorkspaceId(selectedWorkspace?.workspace_id);
    authStorage.setCurrentUser(user);
    setCurrentUser(user);
    if (normalizedWorkspaceId) {
      authStorage.setCurrentWorkspaceId(normalizedWorkspaceId);
      setCurrentWorkspaceId(normalizedWorkspaceId);
      setError(null);
      setStatus("authenticated");
    } else {
      authStorage.setCurrentWorkspaceId(null);
      setCurrentWorkspaceId(null);
      setError("У вас ще немає робочого простору. Створіть перший магазин, щоб почати роботу в Sellora.");
      setStatus("authenticated");
    }
  }, []);

  const reloadCurrentUser = useCallback(async () => {
    const generation = authGeneration.current;
    const isCurrent = () => generation === authGeneration.current;
    const accessToken = authStorage.getAccessToken();
    if (COOKIE_SESSION_AUTH_ENABLED) {
      if (accessToken) {
        try {
          const user = await fetchCurrentUser(accessToken);
          if (isCurrent()) applyUser(user);
          return;
        } catch {
          if (!isCurrent()) return;
          // Recover from an expired short-lived access token using the cookie.
        }
      }
      const tokens = await refreshCookieSession();
      if (!isCurrent()) return;
      authStorage.setTokens(tokens);
      const user = await fetchCurrentUser(tokens.access_token);
      if (isCurrent()) applyUser(user);
      return;
    }
    if (!accessToken) {
      setStatus("unauthenticated");
      return;
    }
    try {
      const user = await fetchCurrentUser(accessToken);
      if (isCurrent()) applyUser(user);
    } catch {
      if (!isCurrent()) return;
      const refreshToken = authStorage.getRefreshToken();
      if (!refreshToken) {
        throw new Error("Session expired");
      }
      const tokens = await refreshAccessToken(refreshToken);
      if (!isCurrent()) return;
      authStorage.setTokens(tokens);
      const user = await fetchCurrentUser(tokens.access_token);
      if (isCurrent()) applyUser(user);
    }
  }, [applyUser]);

  useEffect(() => {
    // An explicit action may precede the initial passive effect.
    if (authGeneration.current !== 0) return;
    const generation = authGeneration.current;
    const restoreFailed = () => {
      if (generation !== authGeneration.current) return;
      authStorage.clear();
      queryClient.clear();
      setCurrentUser(null);
      setCurrentWorkspaceId(null);
      setStatus("unauthenticated");
    };
    if (COOKIE_SESSION_AUTH_ENABLED) {
      // Resume an existing server-side session. The prior JWT migration
      // endpoint has been retired after owner acceptance.
      const pending = (async () => {
        try { await reloadCurrentUser(); }
        catch { restoreFailed(); }
      })();
      // Track every initial attempt, including StrictMode's effect replay.
      // Draining transport also orders old Set-Cookie before a new login/logout.
      bootstrapPending.current = Promise.all([bootstrapPending.current, pending]).then(() => undefined);
      return;
    }
    const storedUser = authStorage.getCurrentUser();
    const storedWorkspaceId = authStorage.getCurrentWorkspaceId();
    if (storedUser && authStorage.getAccessToken()) {
      const selectedWorkspace = storedUser.memberships.find((membership) => normalizeWorkspaceId(membership.workspace_id) === storedWorkspaceId) ?? firstAvailableWorkspace(storedUser);
      const normalizedWorkspaceId = normalizeWorkspaceId(selectedWorkspace?.workspace_id);
      setCurrentUser(storedUser);
      if (normalizedWorkspaceId) authStorage.setCurrentWorkspaceId(normalizedWorkspaceId);
      setCurrentWorkspaceId(normalizedWorkspaceId);
      setStatus("authenticated");
      if (!normalizedWorkspaceId) setError("У вас ще немає робочого простору. Створіть перший магазин, щоб почати роботу в Sellora.");
      void reloadCurrentUser().catch(restoreFailed);
      return;
    }
    setStatus("unauthenticated");
  }, [queryClient, reloadCurrentUser]);

  const login = useCallback(async (email: string, password: string) => {
    const generation = ++authGeneration.current;
    setError(null);
    try {
      if (COOKIE_SESSION_AUTH_ENABLED) await bootstrapPending.current;
      if (generation !== authGeneration.current) return;
      const tokens = await loginWithPassword(email, password);
      if (generation !== authGeneration.current) return;
      const user = await fetchCurrentUser(tokens.access_token);
      if (generation === authGeneration.current) {
        // Keep the previous client actor/credentials together if user verification fails.
        authStorage.setTokens(tokens);
        applyUser(user);
      }
    } catch (error) {
      if (generation === authGeneration.current) {
        setStatus(current => generation === authGeneration.current && current === "loading" ? "unauthenticated" : current);
      }
      throw error;
    }
  }, [applyUser]);

  const logout = useCallback(async () => {
    const generation = ++authGeneration.current;
    if (COOKIE_SESSION_AUTH_ENABLED) await bootstrapPending.current;
    if (generation !== authGeneration.current) return;
    // Do not report successful logout before the server revokes the cookie.
    if (COOKIE_SESSION_AUTH_ENABLED) await revokeCookieSession();
    if (generation !== authGeneration.current) return;
    authStorage.clear();
    queryClient.clear();
    setCurrentUser(null);
    setCurrentWorkspaceId(null);
    setError(null);
    setStatus("unauthenticated");
  }, [queryClient]);

  const switchWorkspace = useCallback((workspaceId: string) => {
    const normalizedWorkspaceId = normalizeWorkspaceId(workspaceId);
    if (!normalizedWorkspaceId || normalizedWorkspaceId === currentWorkspaceId) return;
    void queryClient.cancelQueries();
    authStorage.setCurrentWorkspaceId(normalizedWorkspaceId);
    setCurrentWorkspaceId(normalizedWorkspaceId);
    setError(null);
  }, [currentWorkspaceId, queryClient]);

  const currentWorkspace = useMemo(() => currentUser?.memberships.find((membership) => normalizeWorkspaceId(membership.workspace_id) === currentWorkspaceId) ?? null, [currentUser, currentWorkspaceId]);

  const value = useMemo<AuthContextValue>(() => ({ status, currentUser, currentWorkspaceId, currentWorkspace, error, login, logout, switchWorkspace, reloadCurrentUser }), [status, currentUser, currentWorkspaceId, currentWorkspace, error, login, logout, switchWorkspace, reloadCurrentUser]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
