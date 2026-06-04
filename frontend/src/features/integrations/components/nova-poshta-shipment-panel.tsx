import { CreateTtnButton } from "@/features/integrations/components/create-ttn-button";
import { Shipment } from "@/types/shipments";

export function NovaPoshtaShipmentPanel({ workspaceId, shipment }: { workspaceId: string; shipment: Shipment }) {
  if (shipment.carrier !== "NOVA_POSHTA") return null;
  return <section className="grid gap-3 rounded-xl bg-slate-50 p-3 text-sm"><div className="grid grid-cols-2 gap-2"><span className="text-slate-500">City ref</span><strong className="break-all">{shipment.nova_poshta_city_ref ?? "—"}</strong><span className="text-slate-500">Warehouse ref</span><strong className="break-all">{shipment.nova_poshta_warehouse_ref ?? "—"}</strong><span className="text-slate-500">Document ref</span><strong className="break-all">{shipment.nova_poshta_document_ref ?? "—"}</strong><span className="text-slate-500">Document number</span><strong>{shipment.nova_poshta_document_number ?? "—"}</strong><span className="text-slate-500">Raw status</span><strong>{shipment.nova_poshta_raw_status ?? "—"}</strong></div><CreateTtnButton workspaceId={workspaceId} shipmentId={shipment.id} /></section>;
}
