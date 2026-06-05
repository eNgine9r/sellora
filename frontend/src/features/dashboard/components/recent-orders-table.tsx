import { EmptyState } from "@/components/ui/states";
import { formatMoney } from "@/lib/currency";
import { Order } from "@/types/orders";
import { StatusBadge } from "./status-badge";

export function RecentOrdersTable({ orders, currencyCode = "UAH" }: { orders: Order[]; currencyCode?: string }) {
  const latestOrders = orders.slice(0, 6);

  return (
    <section className="min-w-0 overflow-hidden rounded-[20px] border border-slate-100 bg-white p-4 shadow-[0_18px_45px_rgba(15,23,42,0.06)] dark:border-white/10 dark:bg-slate-900 dark:shadow-none sm:p-5">
      <div className="mb-4 flex min-w-0 items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="break-words text-lg font-black text-slate-950 dark:text-white">Recent orders</h2>
          <p className="break-words text-sm text-slate-500 dark:text-slate-400">Latest customer purchases and fulfillment state.</p>
        </div>
        <span className="shrink-0 rounded-full bg-slate-100 px-3 py-1 text-sm font-bold text-slate-500 dark:bg-white/10 dark:text-slate-200">{latestOrders.length}</span>
      </div>

      {latestOrders.length ? (
        <>
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="text-xs uppercase text-slate-400"><tr><th className="py-2">Order</th><th>Revenue</th><th>Status</th><th>Created</th></tr></thead>
              <tbody>{latestOrders.map((order) => <tr key={order.id} className="border-t border-slate-100 transition hover:bg-slate-50/80 dark:border-white/10 dark:hover:bg-white/5"><td className="max-w-[220px] truncate py-3 font-bold">{order.order_number}</td><td>{formatMoney(order.revenue, currencyCode)}</td><td><StatusBadge value={order.status} /></td><td className="text-slate-500 dark:text-slate-400">{new Date(order.created_at).toLocaleDateString()}</td></tr>)}</tbody>
            </table>
          </div>

          <div className="grid min-w-0 gap-3 md:hidden">
            {latestOrders.map((order) => (
              <article key={order.id} className="min-w-0 overflow-hidden rounded-2xl border border-slate-100 p-4 shadow-sm dark:border-white/10">
                <div className="flex min-w-0 items-start justify-between gap-3">
                  <strong className="min-w-0 truncate text-slate-950 dark:text-white">{order.order_number}</strong>
                  <StatusBadge value={order.status} />
                </div>
                <p className="mt-2 break-words text-sm text-slate-500 dark:text-slate-400">Revenue {formatMoney(order.revenue, currencyCode)}</p>
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
