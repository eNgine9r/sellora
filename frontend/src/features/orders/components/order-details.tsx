import Link from "next/link";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import { Order, OrderStatus } from "@/types/orders";
import { Shipment } from "@/types/shipments";
import { CopyTtnButton } from "@/features/shipments/components/ttn-actions";

const NEXT_STATUSES: OrderStatus[] = [
  "CONFIRMED",
  "SHIPPED",
  "DELIVERED",
  "COMPLETED",
  "RETURNED",
  "CANCELLED",
];

export function OrderDetails({
  order,
  currencyCode = "UAH",
  shipment,
  onStatusChange,
}: {
  order: Order;
  currencyCode?: string;
  shipment?: Shipment | null;
  onStatusChange: (status: OrderStatus) => void;
}) {
  const { t, formatStatus } = useI18n();
  const hasCostContext = Number(order.product_cost) > 0 || Number(order.ad_cost) > 0 || Number(order.shipping_cost) > 0 || Number(order.cod_fee) > 0 || Number(order.other_cost) > 0;
  return (
    <aside className="grid gap-4">
      <div>
        <h2 className="text-xl font-bold">{order.order_number}</h2>
        <p className="text-sm text-text-secondary">
          {t("orders.profit")}: {formatMoney(order.net_profit, currencyCode)}
        </p>
        {!hasCostContext ? (
          <p className="mt-2 rounded-lg bg-amber-50 p-3 text-sm font-semibold text-amber-800 dark:bg-amber-500/15 dark:text-amber-100">
            {t("orders.profitNotCalculated")}
          </p>
        ) : null}
      </div>
      <div className="grid min-w-0 grid-cols-[auto,minmax(0,1fr)] gap-2 text-sm">
        <span>{t("analytics.revenue")}</span>
        <strong>{formatMoney(order.revenue, currencyCode)}</strong>
        <span>{t("orders.productCost")}</span>
        <strong>{formatMoney(order.product_cost, currencyCode)}</strong>
        <span>{t("orders.adCost")}</span>
        <strong>{formatMoney(order.ad_cost, currencyCode)}</strong>
        <span>{t("shipments.shipping")}</span>
        <strong>{formatMoney(order.shipping_cost, currencyCode)}</strong>
        <span>{t("shipments.cod")}</span>
        <strong>{formatMoney(order.cod_fee, currencyCode)}</strong>
        <span>{t("orders.otherCost")}</span>
        <strong>{formatMoney(order.other_cost, currencyCode)}</strong>
        <span>{t("tables.payment")}</span>
        <strong>{formatStatus("payment", order.payment_status)}</strong>
      </div>
      <p className="rounded-xl bg-info-surface p-3 text-sm font-semibold text-info-foreground">
        {t(`orders.paymentHint.${order.payment_status}`)}
      </p>
      <div className="rounded-xl border border-border-subtle bg-surface-1 p-3">
        <h3 className="font-semibold">{t("orders.customerSelector")}</h3>
        {order.customer_id ? (
          <div className="mt-2 grid gap-1 text-sm text-text-secondary">
            <strong className="text-text-primary">
              {order.customer_name ?? t("common.customer")}
            </strong>
            <span>{order.customer_phone ?? "—"}</span>
            {order.customer_instagram_username ? (
              <span>
                @{order.customer_instagram_username.replace(/^@/, "")}
              </span>
            ) : null}
            <Link className="mt-2 inline-flex min-h-10 items-center justify-center rounded-lg border border-border-subtle px-3 py-2 font-bold dark:border-white/10" href="/customers">
              {t("orders.openCustomer")}
            </Link>
          </div>
        ) : (
          <p className="mt-2 rounded-lg bg-amber-50 p-3 text-sm font-semibold text-amber-800 dark:bg-amber-500/15 dark:text-amber-100">
            {t("orders.customerMissing")} {t("shipments.orderCustomerMissing")}
          </p>
        )}
      </div>
      <div className="rounded-xl border border-border-subtle bg-surface-1 p-3">
        <h3 className="font-semibold">{t("orders.campaignLabel")}</h3>
        <p className="mt-2 text-sm text-text-secondary">{order.campaign_name ?? "—"}</p>
      </div>
      <div className="rounded-xl border border-border-subtle bg-surface-1 p-3">
        <h3 className="font-semibold">{t("shipments.details")}</h3>
        {shipment ? (
          <div className="mt-2 grid gap-1 text-sm text-text-secondary">
            <span>
              {t("shipments.tracking")}:{" "}
              {shipment.tracking_number ?? t("shipments.draftShipment")}
            </span>
            <span>
              {t("shipments.carrier")}: {shipment.carrier}
            </span>
            <span>
              {t("tables.status")}: {formatStatus("shipment", shipment.status)}
            </span>
            <span>
              {t("shipments.city")}: {shipment.city ?? "—"}
            </span>
            <span>
              {t("shipments.warehouse")}: {shipment.warehouse ?? "—"}
            </span>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              <Link
                className="inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-4 py-2 font-bold text-primary-foreground hover:bg-primary-hover"
                href="/shipments"
              >
                {t("shipments.openShipments")}
              </Link>
              {shipment.tracking_number ? <CopyTtnButton trackingNumber={shipment.tracking_number} /> : <Link className="inline-flex min-h-11 items-center justify-center rounded-lg border border-border-subtle px-4 py-2 font-bold dark:border-white/10" href={`/shipments?order_id=${order.id}`}>{t("shipments.createTtn")}</Link>}
            </div>
          </div>
        ) : order.customer_id ? (
          <div className="mt-2 grid gap-2">
            <p className="rounded-lg bg-info-surface p-3 text-sm font-semibold text-info-foreground">{t("orders.shipmentMissing")}</p>
            <Link
              className="inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-4 py-2 font-bold text-primary-foreground hover:bg-primary-hover"
              href={`/shipments?order_id=${order.id}`}
            >
              {t("shipments.createFromOrder")}
            </Link>
          </div>
        ) : (
          <p className="mt-2 rounded-lg bg-amber-50 p-3 text-sm font-semibold text-amber-800 dark:bg-amber-500/15 dark:text-amber-100">
            {t("shipments.orderCustomerMissing")}
          </p>
        )}
      </div>
      <div className="grid gap-2">
        <h3 className="font-semibold">{t("orders.items")}</h3>
        {order.items.map((item) => (
          <div
            key={item.id}
            className="rounded-lg border border-border-subtle bg-surface-2 p-3 text-sm text-text-secondary"
          >
            <div className="font-semibold text-text-primary">
              {item.quantity} × {item.product_name}
            </div>
            <div className="mt-1 grid gap-1 sm:grid-cols-2">
              <span>
                {t("products.sku")}: {item.sku}
              </span>
              <span>
                {t("orders.unitPrice")}:{" "}
                {formatMoney(item.unit_price, currencyCode)}
              </span>
              <span>
                {t("orders.lineTotal")}:{" "}
                {formatMoney(item.line_total, currencyCode)}
              </span>
              <span>
                {t("orders.quantity")}: {item.quantity}
              </span>
            </div>
          </div>
        ))}
      </div>
      <div>
        <h3 className="font-semibold">{t("orders.statusHistory")}</h3>
        {order.status_history.map((entry) => (
          <p
            key={entry.id}
            className="text-sm text-text-secondary"
          >
            {entry.from_status ? formatStatus("order", entry.from_status) : "—"}{" "}
            → {formatStatus("order", entry.to_status)}
          </p>
        ))}
      </div>
      <select
        className="min-h-11 rounded-md border border-border-subtle px-3 py-2 dark:border-white/10 dark:bg-white/10"
        value=""
        onChange={(event) =>
          event.target.value &&
          onStatusChange(event.target.value as OrderStatus)
        }
      >
        <option value="">{t("orders.changeStatus")}</option>
        {NEXT_STATUSES.map((status) => (
          <option key={status} value={status}>
            {formatStatus("order", status)}
          </option>
        ))}
      </select>
    </aside>
  );
}
// Order multi-item regression compatibility markers: Unit price, Line total.

// Order detail shipment section regression markers: tracking number shipment status carrier city warehouse copy TTN open shipment create TTN.
