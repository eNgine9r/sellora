import { Shipment } from "@/types/shipments";
import { ShipmentStatusBadge } from "./shipment-status-badge";

export function ShipmentTable({ shipments, onSelect, onEdit }: { shipments: Shipment[]; onSelect: (shipment: Shipment) => void; onEdit?: (shipment: Shipment) => void }) {
  return (
    <section className="rounded-2xl bg-white p-4 shadow-sm">
      <div className="hidden overflow-x-auto md:block">
        <table className="min-w-full text-left text-sm">
          <thead className="text-xs uppercase text-slate-500"><tr>{["Tracking Number", "Order", "Customer", "Carrier", "Status", "City", "Warehouse", "Shipping", "COD", "Created", "Actions"].map((heading) => <th className="px-3 py-2" key={heading}>{heading}</th>)}</tr></thead>
          <tbody>{shipments.map((shipment) => <tr key={shipment.id} className="border-t border-slate-100"><td className="px-3 py-3 font-semibold">{shipment.tracking_number ?? "Draft"}</td><td className="px-3 py-3">{shipment.order_number ?? "—"}</td><td className="px-3 py-3">{shipment.customer_name ?? "—"}</td><td className="px-3 py-3">{shipment.carrier}</td><td className="px-3 py-3"><ShipmentStatusBadge status={shipment.status} /></td><td className="px-3 py-3">{shipment.city ?? "—"}</td><td className="px-3 py-3">{shipment.warehouse ?? "—"}</td><td className="px-3 py-3">{shipment.shipping_cost ?? "—"}</td><td className="px-3 py-3">{shipment.cod_amount ?? "—"}</td><td className="px-3 py-3">{new Date(shipment.created_at).toLocaleDateString()}</td><td className="px-3 py-3"><div className="flex gap-2"><button className="rounded-lg border border-slate-300 px-3 py-2 font-semibold" onClick={() => onSelect(shipment)}>Details</button><button className="rounded-lg border border-slate-300 px-3 py-2 font-semibold" onClick={() => onEdit?.(shipment)}>Edit</button></div></td></tr>)}</tbody>
        </table>
      </div>
      <div className="grid gap-3 md:hidden">
        {shipments.map((shipment) => <article key={shipment.id} className="rounded-2xl border border-slate-200 p-4"><div className="flex items-start justify-between gap-3"><div><p className="text-sm text-slate-500">Tracking</p><h3 className="text-lg font-bold">{shipment.tracking_number ?? "Draft shipment"}</h3></div><ShipmentStatusBadge status={shipment.status} /></div><div className="mt-3 grid gap-1 text-sm text-slate-600"><span>Customer: {shipment.customer_name ?? "—"}</span><span>Order: {shipment.order_number ?? "—"}</span><span>Carrier: {shipment.carrier}</span><span>City: {shipment.city ?? "—"}</span></div><div className="mt-4 grid gap-2"><button className="min-h-11 w-full rounded-xl bg-blue-600 px-4 py-3 font-bold text-white" onClick={() => onSelect(shipment)}>Open details</button><button className="min-h-11 w-full rounded-xl border border-slate-300 px-4 py-3 font-bold" onClick={() => onEdit?.(shipment)}>Edit shipment</button></div></article>)}
      </div>
      {shipments.length === 0 ? <p className="p-6 text-center text-slate-500">No shipments found.</p> : null}
    </section>
  );
}
