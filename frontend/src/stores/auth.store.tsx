"use client";

import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { normalizeWorkspaceId } from "@/lib/workspace";
import { authStorage, fetchCurrentUser, firstAvailableWorkspace, loginWithPassword, refreshAccessToken } from "@/services/auth.service";
import { CurrentUser, WorkspaceMembership } from "@/types/auth";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

type AuthContextValue = {
  status: AuthStatus;
  currentUser: CurrentUser | null;
  currentWorkspaceId: string | null;
  currentWorkspace: WorkspaceMembership | null;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  switchWorkspace: (workspaceId: string) => void;
  reloadCurrentUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
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
    const accessToken = authStorage.getAccessToken();
    if (!accessToken) {
      setStatus("unauthenticated");
      return;
    }
    try {
      const user = await fetchCurrentUser(accessToken);
      applyUser(user);
    } catch {
      const refreshToken = authStorage.getRefreshToken();
      if (!refreshToken) {
        throw new Error("Session expired");
      }
      const tokens = await refreshAccessToken(refreshToken);
      authStorage.setTokens(tokens);
      const user = await fetchCurrentUser(tokens.access_token);
      applyUser(user);
    }
  }, [applyUser]);

  useEffect(() => {
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
      void reloadCurrentUser().catch(() => {
        authStorage.clear();
        queryClient.clear();
        setCurrentUser(null);
        setCurrentWorkspaceId(null);
        setStatus("unauthenticated");
      });
      return;
    }
    setStatus("unauthenticated");
  }, [queryClient, reloadCurrentUser]);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    const tokens = await loginWithPassword(email, password);
    authStorage.setTokens(tokens);
    const user = await fetchCurrentUser(tokens.access_token);
    applyUser(user);
  }, [applyUser]);

  const logout = useCallback(() => {
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
