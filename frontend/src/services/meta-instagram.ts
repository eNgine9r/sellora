import { apiRequest } from "@/services/api";
import { InstagramConnectResponse, InstagramConnectionStatusResponse, InstagramDisconnectResponse, InstagramValidateResponse } from "@/types/meta-instagram";

export function fetchInstagramStatus() {
  return apiRequest<InstagramConnectionStatusResponse>("/integrations/instagram/status");
}

export function startInstagramConnect() {
  return apiRequest<InstagramConnectResponse>("/integrations/instagram/connect", { method: "POST" });
}

export function validateInstagramConnection() {
  return apiRequest<InstagramValidateResponse>("/integrations/instagram/validate", { method: "POST" });
}

export function disconnectInstagram(confirm = false) {
  return apiRequest<InstagramDisconnectResponse>(`/integrations/instagram/disconnect?confirm=${confirm}`, { method: "POST" });
}
