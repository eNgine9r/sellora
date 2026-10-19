import { Shipment } from "@/types/shipments";

export function hasUsableTtn(shipment: Shipment) {
  return shipment.carrier === "NOVA_POSHTA"
    && ["CREATED", "IN_TRANSIT", "ARRIVED", "DELIVERED"].includes(shipment.status)
    && Boolean((shipment.nova_poshta_document_number || shipment.tracking_number)?.trim())
    && !shipment.nova_poshta_manual_reconciliation_required
    && (!shipment.nova_poshta_create_state || shipment.nova_poshta_create_state === "COMPLETED");
}

export function ttnDraftHref(conversationId: string, orderId: string, shipmentId: string) {
  return `/direct?${new URLSearchParams({ conversation: conversationId, ttn_order_id: orderId, ttn_shipment_id: shipmentId })}`;
}
