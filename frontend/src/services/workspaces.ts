import { apiRequest } from "@/services/api";

function workspaceHeaders(workspaceId?: string): HeadersInit {
  return workspaceId ? { "X-Workspace-ID": workspaceId } : {};
}

export type WorkspaceSettings = {
  id: string;
  name: string;
  slug: string;
  currency_code: "UAH" | "USD";
};

export async function fetchWorkspaceSettings(workspaceId: string): Promise<WorkspaceSettings> {
  return apiRequest<WorkspaceSettings>("/workspaces/current", { headers: workspaceHeaders(workspaceId) });
}

export async function updateWorkspaceSettings(workspaceId: string, payload: { name?: string | null; currency_code?: "UAH" | "USD" }): Promise<WorkspaceSettings> {
  return apiRequest<WorkspaceSettings>("/workspaces/current", { method: "PUT", headers: workspaceHeaders(workspaceId), body: JSON.stringify(payload) });
}
