import { apiRequest } from "@/services/api";
import { NovaPoshtaActionResponse, NovaPoshtaDirectoryItem, NovaPoshtaSettings, NovaPoshtaSettingsPayload } from "@/types/integrations";

export const fetchNovaPoshtaSettings = (_workspaceId: string) => apiRequest<NovaPoshtaSettings>("/integrations/nova-poshta/settings");
export const saveNovaPoshtaSettings = (_workspaceId: string, payload: NovaPoshtaSettingsPayload) => apiRequest<NovaPoshtaSettings>("/integrations/nova-poshta/settings", { method: "POST", body: JSON.stringify(payload) });
export const testNovaPoshtaConnection = (_workspaceId: string) => apiRequest<{ success: boolean; message: string; status: string }>("/integrations/nova-poshta/test-connection", { method: "POST" });
export const disconnectNovaPoshta = (_workspaceId: string) => apiRequest<NovaPoshtaSettings>("/integrations/nova-poshta/disconnect", { method: "DELETE" });
export const searchNovaPoshtaCities = (_workspaceId: string, q: string, limit = 20) => apiRequest<NovaPoshtaDirectoryItem[]>(`/integrations/nova-poshta/cities?q=${encodeURIComponent(q)}&limit=${limit}`);
export const searchNovaPoshtaWarehouses = (_workspaceId: string, cityRef: string, q?: string, limit = 50) => apiRequest<NovaPoshtaDirectoryItem[]>(`/integrations/nova-poshta/warehouses?city_ref=${encodeURIComponent(cityRef)}${q ? `&q=${encodeURIComponent(q)}` : ""}&limit=${limit}`);
export const createNovaPoshtaTtn = (_workspaceId: string, shipmentId: string) => apiRequest<NovaPoshtaActionResponse>(`/shipments/${shipmentId}/nova-poshta/create-ttn`, { method: "POST" });
export const syncNovaPoshtaStatus = (_workspaceId: string, shipmentId: string) => apiRequest<NovaPoshtaActionResponse>(`/shipments/${shipmentId}/nova-poshta/sync-status`, { method: "POST" });
