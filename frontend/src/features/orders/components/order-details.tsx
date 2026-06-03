import { Order, OrderStatus } from "@/types/orders";

const NEXT_STATUSES: OrderStatus[] = ["CONFIRMED", "SHIPPED", "DELIVERED", "COMPLETED", "RETURNED", "CANCELLED"];

export function OrderDetails({ order, onStatusChange }: { order: Order; onStatusChange: (status: OrderStatus) => void }) {
  return (
    <aside className="grid gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div><h2 className="text-xl font-bold">{order.order_number}</h2><p className="text-sm text-slate-600">Profit: ${order.net_profit}</p></div>
      <div className="grid grid-cols-2 gap-2 text-sm"><span>Revenue</span><strong>${order.revenue}</strong><span>Product cost</span><strong>${order.product_cost}</strong><span>Ad cost</span><strong>${order.ad_cost}</strong><span>Shipping</span><strong>${order.shipping_cost}</strong><span>COD fee</span><strong>${order.cod_fee}</strong><span>Other</span><strong>${order.other_cost}</strong></div>
      <div><h3 className="font-semibold">Items</h3>{order.items.map((item) => <p key={item.id} className="text-sm text-slate-600">{item.quantity} × {item.product_name} ({item.sku})</p>)}</div>
      <div><h3 className="font-semibold">Status history</h3>{order.status_history.map((entry) => <p key={entry.id} className="text-sm text-slate-600">{entry.from_status ?? "—"} → {entry.to_status}</p>)}</div>
      <select className="rounded-md border border-slate-300 px-3 py-2" value="" onChange={(event) => event.target.value && onStatusChange(event.target.value as OrderStatus)}><option value="">Change status</option>{NEXT_STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}</select>
    </aside>
  );
}
