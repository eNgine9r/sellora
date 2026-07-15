import { apiRequest } from "@/services/api";

function workspaceHeaders(workspaceId?: string): HeadersInit {
  return workspaceId ? { "X-Workspace-ID": workspaceId } : {};
}

export type WorkspaceRole = "OWNER" | "MANAGER" | "ANALYST";
export type CurrencyCode = "UAH" | "USD";

export type WorkspaceSummary = {
  id: string;
  name: string;
  slug: string;
  currency_code: CurrencyCode;
  timezone: string;
  role: WorkspaceRole;
  is_active: boolean;
};

export type WorkspaceSettings = WorkspaceSummary;

export type CreateWorkspacePayload = {
  name: string;
  slug: string;
  currency_code?: CurrencyCode;
  timezone?: string;
};

export type WorkspaceUser = {
  user_id: string;
  email: string;
  full_name: string;
  role: WorkspaceRole;
  is_active: boolean;
};

export type AddWorkspaceUserPayload = {
  email: string;
  full_name: string;
  role: WorkspaceRole;
  temporary_password: string;
};

export async function fetchWorkspaces(): Promise<WorkspaceSummary[]> {
  return apiRequest<WorkspaceSummary[]>("/workspaces");
}

export async function createWorkspace(payload: CreateWorkspacePayload): Promise<WorkspaceSummary> {
  return apiRequest<WorkspaceSummary>("/workspaces", { method: "POST", body: JSON.stringify(payload) });
}

export async function createDemoWorkspace(): Promise<WorkspaceSummary> {
  return apiRequest<WorkspaceSummary>("/workspaces/demo", { method: "POST", body: JSON.stringify({ locale: "uk", currency_code: "UAH" }) });
}

export async function deactivateDemoWorkspace(workspaceId: string): Promise<{ workspace_id: string; is_active: boolean; message: string }> {
  return apiRequest<{ workspace_id: string; is_active: boolean; message: string }>("/workspaces/demo/deactivate", { method: "PATCH", headers: workspaceHeaders(workspaceId) });
}

export async function fetchWorkspaceSettings(workspaceId: string): Promise<WorkspaceSettings> {
  return apiRequest<WorkspaceSettings>("/workspaces/current", { headers: workspaceHeaders(workspaceId) });
}

export async function updateWorkspaceSettings(workspaceId: string, payload: { name?: string | null; slug?: string | null; currency_code?: CurrencyCode | null; timezone?: string | null }): Promise<WorkspaceSettings> {
  return apiRequest<WorkspaceSettings>("/workspaces/current", { method: "PUT", headers: workspaceHeaders(workspaceId), body: JSON.stringify(payload) });
}

export async function fetchWorkspaceUsers(workspaceId: string): Promise<WorkspaceUser[]> {
  return apiRequest<WorkspaceUser[]>("/workspace-users", { headers: workspaceHeaders(workspaceId) });
}

export async function addWorkspaceUser(workspaceId: string, payload: AddWorkspaceUserPayload): Promise<WorkspaceUser> {
  return apiRequest<WorkspaceUser>("/workspace-users", { method: "POST", headers: workspaceHeaders(workspaceId), body: JSON.stringify(payload) });
}

export async function updateWorkspaceUserRole(workspaceId: string, userId: string, role: WorkspaceRole): Promise<WorkspaceUser> {
  return apiRequest<WorkspaceUser>(`/workspace-users/${userId}/role`, { method: "PUT", headers: workspaceHeaders(workspaceId), body: JSON.stringify({ role }) });
}

export async function deactivateWorkspaceUser(workspaceId: string, userId: string): Promise<WorkspaceUser> {
  return apiRequest<WorkspaceUser>(`/workspace-users/${userId}/deactivate`, { method: "PATCH", headers: workspaceHeaders(workspaceId) });
}

export const roleLabels: Record<WorkspaceRole, string> = {
  OWNER: "Власник",
  MANAGER: "Менеджер",
  ANALYST: "Аналітик",
};
