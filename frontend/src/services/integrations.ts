import { apiRequest } from "@/services/api";
import { NovaPoshtaActionResponse, NovaPoshtaDirectoryItem, NovaPoshtaSettings, NovaPoshtaSettingsPayload } from "@/types/integrations";

function withWorkspaceContext<T>(workspaceId: string, request: () => Promise<T>) {
  void workspaceId;
  return request();
}

export const fetchNovaPoshtaSettings = (workspaceId: string) => withWorkspaceContext(workspaceId, () => apiRequest<NovaPoshtaSettings>("/integrations/nova-poshta/settings"));
export const saveNovaPoshtaSettings = (workspaceId: string, payload: NovaPoshtaSettingsPayload) => withWorkspaceContext(workspaceId, () => apiRequest<NovaPoshtaSettings>("/integrations/nova-poshta/settings", { method: "POST", body: JSON.stringify(payload) }));
export const testNovaPoshtaConnection = (workspaceId: string) => withWorkspaceContext(workspaceId, () => apiRequest<{ success: boolean; message: string; status: string }>("/integrations/nova-poshta/test-connection", { method: "POST" }));
export const disconnectNovaPoshta = (workspaceId: string) => withWorkspaceContext(workspaceId, () => apiRequest<NovaPoshtaSettings>("/integrations/nova-poshta/disconnect", { method: "DELETE" }));
export const searchNovaPoshtaCities = (workspaceId: string, q: string, limit = 20) => withWorkspaceContext(workspaceId, () => apiRequest<NovaPoshtaDirectoryItem[]>(`/integrations/nova-poshta/cities?q=${encodeURIComponent(q)}&limit=${limit}`));
export const searchNovaPoshtaWarehouses = (workspaceId: string, cityRef: string, q?: string, limit = 50) => withWorkspaceContext(workspaceId, () => apiRequest<NovaPoshtaDirectoryItem[]>(`/integrations/nova-poshta/warehouses?city_ref=${encodeURIComponent(cityRef)}${q ? `&q=${encodeURIComponent(q)}` : ""}&limit=${limit}`));
export const createNovaPoshtaTtn = (workspaceId: string, shipmentId: string) => withWorkspaceContext(workspaceId, () => apiRequest<NovaPoshtaActionResponse>(`/shipments/${shipmentId}/nova-poshta/create-ttn`, { method: "POST" }));
export const reconcileNovaPoshtaTtn = (workspaceId: string, shipmentId: string) => withWorkspaceContext(workspaceId, () => apiRequest<NovaPoshtaActionResponse>(`/shipments/${shipmentId}/nova-poshta/reconcile-ttn`, { method: "POST" }));
export const syncNovaPoshtaStatus = (workspaceId: string, shipmentId: string) => withWorkspaceContext(workspaceId, () => apiRequest<NovaPoshtaActionResponse>(`/shipments/${shipmentId}/nova-poshta/sync-status`, { method: "POST" }));
