import { apiRequest } from "@/services/api";
import { WorkspaceMemo, WorkspaceMemoCreate, WorkspaceMemoUpdate } from "@/types/workspace-memo";

const headers = (workspaceId: string) => ({ "X-Workspace-ID": workspaceId });
export function fetchWorkspaceMemos(workspaceId: string) {
  return apiRequest<WorkspaceMemo[]>("/workspace-memos", { headers: headers(workspaceId) });
}
export function createWorkspaceMemo(workspaceId: string, payload: WorkspaceMemoCreate) {
  return apiRequest<WorkspaceMemo>("/workspace-memos", {
    method: "POST", headers: headers(workspaceId), body: JSON.stringify(payload),
  });
}
export function updateWorkspaceMemo(workspaceId: string, id: string, payload: WorkspaceMemoUpdate) {
  return apiRequest<WorkspaceMemo>(`/workspace-memos/${id}`, {
    method: "PATCH", headers: headers(workspaceId), body: JSON.stringify(payload),
  });
}
export function deleteWorkspaceMemo(workspaceId: string, id: string) {
  return apiRequest<void>(`/workspace-memos/${id}`, {
    method: "DELETE", headers: headers(workspaceId),
  });
}
