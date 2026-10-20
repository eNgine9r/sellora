import { apiRequest as sharedApiRequest } from "@/services/api";
import {
  NovaPoshtaActionResponse,
  NovaPoshtaDirectoryItem,
  NovaPoshtaReadiness,
  NovaPoshtaSettings,
  NovaPoshtaSettingsPayload,
} from "@/types/integrations";

function withWorkspaceContext<T>(workspaceId: string, request: (apiRequest: typeof sharedApiRequest) => Promise<T>) {
  return request((path, init) => sharedApiRequest(path, { ...init, headers: { ...init?.headers, "X-Workspace-ID": workspaceId } }));
}

export const fetchNovaPoshtaSettings = (workspaceId: string) => withWorkspaceContext(workspaceId, (apiRequest) => apiRequest<NovaPoshtaSettings>("/integrations/nova-poshta/settings"));
export const fetchNovaPoshtaReadiness = (workspaceId: string) => withWorkspaceContext(
  workspaceId,
  (apiRequest) => apiRequest<NovaPoshtaReadiness>("/integrations/nova-poshta/readiness"),
);
export const saveNovaPoshtaSettings = (workspaceId: string, payload: NovaPoshtaSettingsPayload) => withWorkspaceContext(workspaceId, (apiRequest) => apiRequest<NovaPoshtaSettings>("/integrations/nova-poshta/settings", { method: "POST", body: JSON.stringify(payload) }));
export const updateNovaPoshtaWritePermission = (workspaceId: string, allowed: boolean) => withWorkspaceContext(
  workspaceId,
  (apiRequest) => apiRequest<NovaPoshtaSettings>("/integrations/nova-poshta/write-permission", {
    method: "PATCH",
    body: JSON.stringify({ allowed }),
  }),
);
export const testNovaPoshtaConnection = (workspaceId: string) => withWorkspaceContext(
  workspaceId,
  (apiRequest) => apiRequest<{ success: boolean; message: string; status: string; errors: string[] }>(
    "/integrations/nova-poshta/test-connection",
    { method: "POST" },
  ),
);
export const disconnectNovaPoshta = (workspaceId: string) => withWorkspaceContext(workspaceId, (apiRequest) => apiRequest<NovaPoshtaSettings>("/integrations/nova-poshta/disconnect", { method: "DELETE" }));
export const searchNovaPoshtaCities = (workspaceId: string, q: string, limit = 20) => withWorkspaceContext(workspaceId, (apiRequest) => apiRequest<NovaPoshtaDirectoryItem[]>(`/integrations/nova-poshta/cities?q=${encodeURIComponent(q)}&limit=${limit}`));
export const searchNovaPoshtaWarehouses = (workspaceId: string, cityRef: string, q?: string, limit = 50) => withWorkspaceContext(workspaceId, (apiRequest) => apiRequest<NovaPoshtaDirectoryItem[]>(`/integrations/nova-poshta/warehouses?city_ref=${encodeURIComponent(cityRef)}${q ? `&q=${encodeURIComponent(q)}` : ""}&limit=${limit}`));
export const createNovaPoshtaTtn = (workspaceId: string, shipmentId: string) => withWorkspaceContext(workspaceId, (apiRequest) => apiRequest<NovaPoshtaActionResponse>(`/shipments/${shipmentId}/nova-poshta/create-ttn`, { method: "POST" }));
export const reconcileNovaPoshtaTtn = (workspaceId: string, shipmentId: string) => withWorkspaceContext(workspaceId, (apiRequest) => apiRequest<NovaPoshtaActionResponse>(`/shipments/${shipmentId}/nova-poshta/reconcile-ttn`, { method: "POST" }));
export const syncNovaPoshtaStatus = (workspaceId: string, shipmentId: string) => withWorkspaceContext(workspaceId, (apiRequest) => apiRequest<NovaPoshtaActionResponse>(`/shipments/${shipmentId}/nova-poshta/sync-status`, { method: "POST" }));

export const searchNovaPoshtaSenders = (workspaceId: string, q = "", page = 1) => withWorkspaceContext(workspaceId, (apiRequest) => apiRequest<NovaPoshtaDirectoryItem[]>(`/integrations/nova-poshta/senders?q=${encodeURIComponent(q)}&page=${page}&limit=20`));
export const fetchNovaPoshtaSenderContacts = (workspaceId: string, senderRef: string) => withWorkspaceContext(workspaceId, (apiRequest) => apiRequest<NovaPoshtaDirectoryItem[]>(`/integrations/nova-poshta/sender-contacts?sender_ref=${encodeURIComponent(senderRef)}`));
