import { Order } from "@/types/orders";

export function OrderTable({ orders, onSelect }: { orders: Order[]; onSelect: (order: Order) => void }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
          <tr><th className="px-4 py-3">Order</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Payment</th><th className="px-4 py-3">Revenue</th><th className="px-4 py-3">Profit</th><th className="px-4 py-3">Created</th></tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {orders.map((order) => <tr key={order.id} className="cursor-pointer hover:bg-slate-50" onClick={() => onSelect(order)}><td className="px-4 py-3 font-medium">{order.order_number}</td><td className="px-4 py-3">{order.status}</td><td className="px-4 py-3">{order.payment_status}</td><td className="px-4 py-3">${order.revenue}</td><td className="px-4 py-3">${order.net_profit}</td><td className="px-4 py-3">{new Date(order.created_at).toLocaleDateString()}</td></tr>)}
          {orders.length === 0 ? <tr><td className="px-4 py-8 text-center text-slate-500" colSpan={6}>No orders found.</td></tr> : null}
        </tbody>
      </table>
    </div>
  );
}
