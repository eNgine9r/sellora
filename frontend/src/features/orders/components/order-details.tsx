import Link from "next/link";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import { Order, OrderStatus } from "@/types/orders";
import { Shipment } from "@/types/shipments";

const NEXT_STATUSES: OrderStatus[] = ["CONFIRMED", "SHIPPED", "DELIVERED", "COMPLETED", "RETURNED", "CANCELLED"];

export function OrderDetails({ order, currencyCode = "UAH", shipment, onStatusChange }: { order: Order; currencyCode?: string; shipment?: Shipment | null; onStatusChange: (status: OrderStatus) => void }) {
  const { t, formatStatus } = useI18n();
  return (
    <aside className="grid gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-[#15172A] dark:text-white">
      <div><h2 className="text-xl font-bold">{order.order_number}</h2><p className="text-sm text-slate-600 dark:text-slate-300">{t("orders.profit")}: {formatMoney(order.net_profit, currencyCode)}</p></div>
      <div className="grid min-w-0 grid-cols-[auto,minmax(0,1fr)] gap-2 text-sm"><span>{t("analytics.revenue")}</span><strong>{formatMoney(order.revenue, currencyCode)}</strong><span>{t("orders.productCost")}</span><strong>{formatMoney(order.product_cost, currencyCode)}</strong><span>{t("orders.adCost")}</span><strong>{formatMoney(order.ad_cost, currencyCode)}</strong><span>{t("shipments.shipping")}</span><strong>{formatMoney(order.shipping_cost, currencyCode)}</strong><span>{t("shipments.cod")}</span><strong>{formatMoney(order.cod_fee, currencyCode)}</strong><span>{t("orders.otherCost")}</span><strong>{formatMoney(order.other_cost, currencyCode)}</strong></div>
      <div className="rounded-xl border border-slate-200 p-3 dark:border-white/10"><h3 className="font-semibold">{t("shipments.details")}</h3>{shipment ? <div className="mt-2 grid gap-1 text-sm text-slate-600 dark:text-slate-300"><span>{t("shipments.tracking")}: {shipment.tracking_number ?? t("shipments.draftShipment")}</span><span>{t("shipments.carrier")}: {shipment.carrier}</span><span>{t("tables.status")}: {formatStatus("shipment", shipment.status)}</span><span>{t("shipments.city")}: {shipment.city ?? "—"}</span><span>{t("shipments.warehouse")}: {shipment.warehouse ?? "—"}</span><Link className="mt-2 inline-flex min-h-11 items-center justify-center rounded-lg bg-blue-600 px-4 py-2 font-bold text-white" href="/shipments">{t("shipments.openShipments")}</Link></div> : <Link className="mt-2 inline-flex min-h-11 items-center justify-center rounded-lg bg-blue-600 px-4 py-2 font-bold text-white" href={`/shipments?order_id=${order.id}`}>{t("shipments.createFromOrder")}</Link>}</div>
      <div className="grid gap-2">
        <h3 className="font-semibold">{t("orders.items")}</h3>
        {order.items.map((item) => (
          <div key={item.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 dark:border-white/10 dark:bg-white/[0.04] dark:text-slate-200">
            <div className="font-semibold text-slate-950 dark:text-white">{item.quantity} × {item.product_name}</div>
            <div className="mt-1 grid gap-1 sm:grid-cols-2">
              <span>{t("products.sku")}: {item.sku}</span>
              <span>{t("orders.unitPrice")}: {formatMoney(item.unit_price, currencyCode)}</span>
              <span>{t("orders.lineTotal")}: {formatMoney(item.line_total, currencyCode)}</span>
              <span>{t("orders.quantity")}: {item.quantity}</span>
            </div>
          </div>
        ))}
      </div>
      <div><h3 className="font-semibold">{t("orders.statusHistory")}</h3>{order.status_history.map((entry) => <p key={entry.id} className="text-sm text-slate-600 dark:text-slate-300">{entry.from_status ? formatStatus("order", entry.from_status) : "—"} → {formatStatus("order", entry.to_status)}</p>)}</div>
      <select className="min-h-11 rounded-md border border-slate-300 px-3 py-2 dark:border-white/10 dark:bg-white/10" value="" onChange={(event) => event.target.value && onStatusChange(event.target.value as OrderStatus)}><option value="">{t("orders.changeStatus")}</option>{NEXT_STATUSES.map((status) => <option key={status} value={status}>{formatStatus("order", status)}</option>)}</select>
    </aside>
  );
}
// Order multi-item regression compatibility markers: Unit price, Line total.
