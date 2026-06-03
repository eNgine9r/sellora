"use client";

import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
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
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [currentWorkspaceId, setCurrentWorkspaceId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const applyUser = useCallback((user: CurrentUser) => {
    const storedWorkspaceId = authStorage.getCurrentWorkspaceId();
    const selectedWorkspace = user.memberships.find((membership) => membership.workspace_id === storedWorkspaceId) ?? firstAvailableWorkspace(user);
    authStorage.setCurrentUser(user);
    setCurrentUser(user);
    if (selectedWorkspace) {
      authStorage.setCurrentWorkspaceId(selectedWorkspace.workspace_id);
      setCurrentWorkspaceId(selectedWorkspace.workspace_id);
      setError(null);
      setStatus("authenticated");
    } else {
      setCurrentWorkspaceId(null);
      setError("Your account is not assigned to an active workspace yet.");
      setStatus("unauthenticated");
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
      setCurrentUser(storedUser);
      setCurrentWorkspaceId(storedWorkspaceId);
      setStatus("authenticated");
      void reloadCurrentUser().catch(() => {
        authStorage.clear();
        setCurrentUser(null);
        setCurrentWorkspaceId(null);
        setStatus("unauthenticated");
      });
      return;
    }
    setStatus("unauthenticated");
  }, [reloadCurrentUser]);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    const tokens = await loginWithPassword(email, password);
    authStorage.setTokens(tokens);
    const user = await fetchCurrentUser(tokens.access_token);
    applyUser(user);
  }, [applyUser]);

  const logout = useCallback(() => {
    authStorage.clear();
    setCurrentUser(null);
    setCurrentWorkspaceId(null);
    setError(null);
    setStatus("unauthenticated");
  }, []);

  const switchWorkspace = useCallback((workspaceId: string) => {
    const workspace = currentUser?.memberships.find((membership) => membership.workspace_id === workspaceId);
    if (!workspace) return;
    authStorage.setCurrentWorkspaceId(workspaceId);
    setCurrentWorkspaceId(workspaceId);
  }, [currentUser]);

  const currentWorkspace = useMemo(() => currentUser?.memberships.find((membership) => membership.workspace_id === currentWorkspaceId) ?? null, [currentUser, currentWorkspaceId]);

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
