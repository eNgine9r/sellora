"use client";

import Link from "next/link";
import { ArrowUpRight, ChevronRight } from "lucide-react";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import type { Order } from "@/types/orders";
import { StatusBadge } from "./status-badge";

type Props = {
  orders: Order[];
  currencyCode?: string;
  showProfit?: boolean;
  isLoading?: boolean;
  isError?: boolean;
  onRetry?: () => void;
};

export function RecentOrdersTable({ orders, currencyCode = "UAH", showProfit = false, isLoading = false, isError = false, onRetry }: Props) {
  const { t, formatStatus, locale } = useI18n();
  // Latest across all periods. Never crop the unsorted input before sorting.
  const latestOrders = [...orders]
    .sort((left, right) => right.created_at.localeCompare(left.created_at))
    .slice(0, 4);
  const dateLocale = locale === "en" ? "en-GB" : "uk-UA";

  return (
    <section data-dashboard-recent-orders className="min-w-0 overflow-hidden rounded-xl border border-border-subtle bg-surface-1 p-3 sm:p-4">
      <header className="flex min-w-0 items-center justify-between gap-2">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-text-primary sm:text-base">{t("dashboard.recentOrders.title")}</h2>
          <p title={t("dashboard.recentOrders.subtitle")} className="mt-0.5 text-[11px] text-text-muted">{t("dashboard.recentOrders.allDates")}</p>
        </div>
        <Link href="/orders" className="inline-flex min-h-9 shrink-0 items-center gap-1 rounded-lg px-2 text-xs font-semibold text-primary transition hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring">
          {t("dashboard.recentOrders.viewAll")} <ArrowUpRight aria-hidden="true" className="h-3.5 w-3.5" />
        </Link>
      </header>
      {isLoading ? (
        <div className="mt-3 grid gap-2" aria-busy="true" aria-label={t("dashboard.loading.orders")}>
          {Array.from({ length: 3 }, (_, index) => (
            <div key={index} className="flex min-h-10 items-center justify-between gap-3 rounded-lg border border-border-subtle/60 px-3">
              <span className="h-3 w-24 animate-pulse rounded-full bg-surface-3 motion-reduce:animate-none" />
              <span className="h-3 w-14 animate-pulse rounded-full bg-surface-3 motion-reduce:animate-none" />
            </div>
          ))}
        </div>
      ) : isError ? (
        <div role="status" className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-lg bg-surface-2 p-3 text-xs text-text-secondary">
          <span>{t("dashboard.errors.loadFailed")}</span>
          {onRetry ? <button type="button" onClick={onRetry} className="font-semibold text-primary underline">{t("dashboard.recentOrders.retry")}</button> : null}
        </div>
      ) : latestOrders.length ? (
        <ul className="mt-3 divide-y divide-border-subtle" data-dashboard-recent-orders-list>
          {latestOrders.map((order) => (
            <li key={order.id}>
              <Link href={`/orders?order_id=${encodeURIComponent(order.id)}`} className="group flex min-w-0 items-center gap-2 rounded-lg px-1 py-2 transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring sm:gap-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-semibold text-text-primary sm:text-sm">{order.order_number}</p>
                  <p className="mt-0.5 text-[11px] text-text-muted">{new Date(order.created_at).toLocaleDateString(dateLocale)}</p>
                </div>
                <span className="hidden min-w-0 shrink-0 sm:inline-flex"><StatusBadge value={order.status} /></span>
                <div className="min-w-0 shrink-0 text-right">
                  <p className="whitespace-nowrap text-xs font-semibold tabular-nums text-text-primary sm:text-sm">{formatMoney(order.revenue, currencyCode)}</p>
                  {showProfit && order.net_profit != null ? <p className="text-[11px] tabular-nums text-text-muted" title={t("tables.profit")}>{formatMoney(order.net_profit, currencyCode)}</p> : null}
                  <p className="text-[10px] text-text-muted sm:hidden">{formatStatus("order", order.status)}</p>
                </div>
                <ChevronRight aria-hidden="true" className="h-3.5 w-3.5 shrink-0 text-text-muted transition-transform group-hover:translate-x-0.5" />
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 rounded-lg bg-surface-2 p-3 text-xs text-text-secondary">{t("dashboard.emptyStates.noRecentOrders")}</p>
      )}
    </section>
  );
}
