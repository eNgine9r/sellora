import { Shipment, ShipmentStatus } from "@/types/shipments";
import { NovaPoshtaShipmentPanel } from "@/features/integrations/components/nova-poshta-shipment-panel";
import { ShipmentStatusBadge } from "./shipment-status-badge";

const NEXT_ACTIONS: Record<ShipmentStatus, ShipmentStatus[]> = {
  DRAFT: ["CREATED", "CANCELLED"],
  CREATED: ["IN_TRANSIT", "CANCELLED"],
  IN_TRANSIT: ["ARRIVED", "DELIVERED", "RETURNED"],
  ARRIVED: ["DELIVERED", "RETURNED"],
  DELIVERED: ["RETURNED"],
  RETURNED: [],
  CANCELLED: [],
};

export function ShipmentDetails({ shipment, workspaceId, onStatusChange }: { shipment: Shipment; workspaceId: string; onStatusChange: (status: ShipmentStatus) => void }) {
  const actions = NEXT_ACTIONS[shipment.status];
  return (
    <aside className="grid min-w-0 gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div><p className="text-sm text-slate-500">Shipment</p><h2 className="break-all text-xl font-bold">{shipment.tracking_number ?? "Draft shipment"}</h2></div><ShipmentStatusBadge status={shipment.status} /></div>
      <div className="grid min-w-0 grid-cols-[auto,minmax(0,1fr)] gap-2 text-sm"><span className="text-slate-500">Order</span><strong className="min-w-0 break-words">{shipment.order_number ?? "—"}</strong><span className="text-slate-500">Customer</span><strong className="min-w-0 break-words">{shipment.customer_name ?? "—"}</strong><span className="text-slate-500">Carrier</span><strong className="min-w-0 break-words">{shipment.carrier}</strong><span className="text-slate-500">City</span><strong className="min-w-0 break-words">{shipment.city ?? "—"}</strong><span className="text-slate-500">Warehouse</span><strong className="min-w-0 break-words">{shipment.warehouse ?? "—"}</strong><span className="text-slate-500">Shipping</span><strong className="min-w-0 break-words">{shipment.shipping_cost ?? "—"}</strong><span className="text-slate-500">COD</span><strong className="min-w-0 break-words">{shipment.cod_amount ?? "—"}</strong></div>
      <div className="grid gap-1 text-sm text-slate-600"><span>Shipped: {shipment.shipped_at ? new Date(shipment.shipped_at).toLocaleString() : "—"}</span><span>Delivered: {shipment.delivered_at ? new Date(shipment.delivered_at).toLocaleString() : "—"}</span><span>Returned: {shipment.returned_at ? new Date(shipment.returned_at).toLocaleString() : "—"}</span></div>
      {shipment.notes ? <p className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600">{shipment.notes}</p> : null}<NovaPoshtaShipmentPanel workspaceId={workspaceId} shipment={shipment} />
      {actions.length ? <div className="grid gap-2 sm:grid-cols-2">{actions.map((status) => <button key={status} className="min-h-11 rounded-xl border border-slate-300 px-4 py-3 text-sm font-bold hover:bg-slate-50" onClick={() => onStatusChange(status)}>{status.replaceAll("_", " ")}</button>)}</div> : <p className="text-sm text-slate-500">No next shipment actions available.</p>}
    </aside>
  );
}
