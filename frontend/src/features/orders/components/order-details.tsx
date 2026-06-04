import Link from "next/link";
import { Order, OrderStatus } from "@/types/orders";
import { Shipment } from "@/types/shipments";

const NEXT_STATUSES: OrderStatus[] = ["CONFIRMED", "SHIPPED", "DELIVERED", "COMPLETED", "RETURNED", "CANCELLED"];
const money = (value: string | number) => Number(value).toFixed(2);

export function OrderDetails({ order, shipment, onStatusChange }: { order: Order; shipment?: Shipment | null; onStatusChange: (status: OrderStatus) => void }) {
  return (
    <aside className="grid gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div><h2 className="text-xl font-bold">{order.order_number}</h2><p className="text-sm text-slate-600">Profit: ${order.net_profit}</p></div>
      <div className="grid grid-cols-2 gap-2 text-sm"><span>Revenue</span><strong>${order.revenue}</strong><span>Product cost</span><strong>${order.product_cost}</strong><span>Ad cost</span><strong>${order.ad_cost}</strong><span>Shipping</span><strong>${order.shipping_cost}</strong><span>COD fee</span><strong>${order.cod_fee}</strong><span>Other</span><strong>${order.other_cost}</strong></div>
      <div className="rounded-xl border border-slate-200 p-3"><h3 className="font-semibold">Shipment</h3>{shipment ? <div className="mt-2 grid gap-1 text-sm text-slate-600"><span>Tracking: {shipment.tracking_number ?? "Draft"}</span><span>Carrier: {shipment.carrier}</span><span>Status: {shipment.status}</span><span>City: {shipment.city ?? "—"}</span><span>Warehouse: {shipment.warehouse ?? "—"}</span><Link className="mt-2 inline-flex min-h-11 items-center justify-center rounded-lg bg-blue-600 px-4 py-2 font-bold text-white" href="/shipments">Open shipments</Link></div> : <Link className="mt-2 inline-flex min-h-11 items-center justify-center rounded-lg bg-blue-600 px-4 py-2 font-bold text-white" href={`/shipments?order_id=${order.id}`}>Create Shipment</Link>}</div>
      <div className="grid gap-2">
        <h3 className="font-semibold">Items</h3>
        {order.items.map((item) => (
          <div key={item.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
            <div className="font-semibold text-slate-950">{item.quantity} × {item.product_name}</div>
            <div className="mt-1 grid gap-1 sm:grid-cols-2">
              <span>SKU: {item.sku}</span>
              <span>Unit price: {money(item.unit_price)}</span>
              <span>Line total: {money(item.line_total)}</span>
              <span>Quantity: {item.quantity}</span>
            </div>
          </div>
        ))}
      </div>
      <div><h3 className="font-semibold">Status history</h3>{order.status_history.map((entry) => <p key={entry.id} className="text-sm text-slate-600">{entry.from_status ?? "—"} → {entry.to_status}</p>)}</div>
      <select className="min-h-11 rounded-md border border-slate-300 px-3 py-2" value="" onChange={(event) => event.target.value && onStatusChange(event.target.value as OrderStatus)}><option value="">Change status</option>{NEXT_STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}</select>
    </aside>
  );
}
