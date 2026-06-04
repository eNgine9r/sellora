import { EmptyState } from "@/components/ui/states";
import { Order } from "@/types/orders";
import { StatusBadge } from "./status-badge";

export function RecentOrdersTable({ orders }: { orders: Order[] }) {
  const latestOrders = orders.slice(0, 6);

  return (
    <section className="rounded-[20px] border border-slate-100 bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.06)]">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-black">Recent orders</h2>
          <p className="text-sm text-slate-500">Latest customer purchases and fulfillment state.</p>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-bold text-slate-500">{latestOrders.length}</span>
      </div>

      {latestOrders.length ? (
        <>
          <div className="hidden overflow-x-auto md:block">
            <table className="min-w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-400">
                <tr>
                  <th className="py-2">Order</th>
                  <th>Revenue</th>
                  <th>Status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {latestOrders.map((order) => (
                  <tr key={order.id} className="border-t border-slate-100 transition hover:bg-slate-50/80">
                    <td className="py-3 font-bold">{order.order_number}</td>
                    <td>${order.revenue}</td>
                    <td>
                      <StatusBadge value={order.status} />
                    </td>
                    <td className="text-slate-500">{new Date(order.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid gap-3 md:hidden">
            {latestOrders.map((order) => (
              <article key={order.id} className="rounded-2xl border border-slate-100 p-4 shadow-sm">
                <div className="flex items-center justify-between gap-3">
                  <strong>{order.order_number}</strong>
                  <StatusBadge value={order.status} />
                </div>
                <p className="mt-2 text-sm text-slate-500">Revenue ${order.revenue}</p>
                <p className="mt-1 text-xs text-slate-400">{new Date(order.created_at).toLocaleDateString()}</p>
              </article>
            ))}
          </div>
        </>
      ) : (
        <EmptyState title="No orders yet" description="Create your first order or import historical data to start tracking revenue and fulfillment." />
      )}
    </section>
  );
}
