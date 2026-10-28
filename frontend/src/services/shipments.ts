import { apiRequest } from "@/services/api";
import { Shipment, ShipmentCreatePayload, ShipmentStatus, ShipmentSummary } from "@/types/shipments";

function workspaceHeaders(workspaceId?: string): HeadersInit {
  return workspaceId ? { "X-Workspace-ID": workspaceId } : {};
}

export async function fetchShipments(workspaceId: string, status?: ShipmentStatus | "", search?: string): Promise<Shipment[]> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (search?.trim()) params.set("search", search.trim());
  const query = params.toString();
  return apiRequest<Shipment[]>(`/shipments${query ? `?${query}` : ""}`, { headers: workspaceHeaders(workspaceId) });
}

export async function fetchShipmentSummary(workspaceId: string): Promise<ShipmentSummary> {
  return apiRequest<ShipmentSummary>("/shipments/summary", { headers: workspaceHeaders(workspaceId) });
}

export async function updateShipment(workspaceId: string, shipmentId: string, payload: Partial<Omit<ShipmentCreatePayload, "order_id">>): Promise<Shipment> {
  return apiRequest<Shipment>(`/shipments/${shipmentId}`, { method: "PUT", headers: workspaceHeaders(workspaceId), body: JSON.stringify(payload) });
}

export async function createShipment(workspaceId: string, payload: ShipmentCreatePayload): Promise<Shipment> {
  return apiRequest<Shipment>("/shipments", { method: "POST", headers: workspaceHeaders(workspaceId), body: JSON.stringify(payload) });
}

export async function fetchOrderShipment(workspaceId: string, orderId: string): Promise<Shipment | null> {
  return apiRequest<Shipment | null>(`/orders/${orderId}/shipment`, { headers: workspaceHeaders(workspaceId) });
}

export async function changeShipmentStatus(workspaceId: string, shipmentId: string, status: ShipmentStatus): Promise<Shipment> {
  const pathByStatus: Record<ShipmentStatus, string> = {
    DRAFT: "",
    CREATED: "mark-created",
    IN_TRANSIT: "mark-in-transit",
    ARRIVED: "mark-arrived",
    DELIVERED: "mark-delivered",
    RETURNED: "mark-returned",
    CANCELLED: "cancel",
  };
  const action = pathByStatus[status];
  if (!action) throw new Error("Draft status cannot be applied through shipment status actions");
  return apiRequest<Shipment>(`/shipments/${shipmentId}/${action}`, { method: "POST", headers: workspaceHeaders(workspaceId) });
}

export async function deleteShipment(workspaceId: string, shipmentId: string): Promise<void> {
  return apiRequest<void>(`/shipments/${shipmentId}`, { method: "DELETE", headers: workspaceHeaders(workspaceId) });
}

export type ExternalNovaPoshtaDocument = {
  id: string;
  tracking_number: string;
  provider_status: string | null;
  match_state: "UNMATCHED" | "LINKED" | "CONFLICT";
  matched_shipment_id: string | null;
  last_seen_at: string;
};
export type ExternalNovaPoshtaScanResult = {
  scanned: number; unmatched: number; linked: number; conflicts: number; dry_run: boolean;
};

export async function fetchExternalNovaPoshtaDocuments(
  workspaceId: string,
  matchState: "UNMATCHED" | "CONFLICT",
): Promise<ExternalNovaPoshtaDocument[]> {
  return apiRequest<ExternalNovaPoshtaDocument[]>(
    "/integrations/nova-poshta/external-documents?match_state=" + matchState,
    { headers: workspaceHeaders(workspaceId) },
  );
}

export async function scanExternalNovaPoshtaDocuments(
  workspaceId: string, fromDate: string, toDate: string,
): Promise<ExternalNovaPoshtaScanResult> {
  return apiRequest<ExternalNovaPoshtaScanResult>(
    "/integrations/nova-poshta/external-documents/scan",
    {
      method: "POST",
      headers: workspaceHeaders(workspaceId),
      body: JSON.stringify({ from_date: fromDate, to_date: toDate, dry_run: false }),
    },
  );
}
