"use client";

import { useQuery } from "@tanstack/react-query";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import { fetchCrmAttribution } from "@/services/advertising";
import { CrmAttributionTotals } from "@/types/advertising";

export function CrmAttributionSection({ workspaceId, enabled, startDate, endDate, currencyCode }: {
  workspaceId: string; enabled: boolean; startDate: string; endDate: string; currencyCode: string;
}) {
  const { t } = useI18n();
  const label = (key: string) => t(`advertising.crm.${key}`);
  const invalid = Boolean(startDate && endDate && startDate > endDate);
  const report = useQuery({
    queryKey: ["ad-crm-attribution", workspaceId, startDate, endDate],
    queryFn: () => fetchCrmAttribution(workspaceId, undefined, startDate, endDate),
    enabled: enabled && !invalid,
  });
  const money = (value: string | null) => value === null ? "—" : formatMoney(value, currencyCode);
  const data = report.data;
  const stats = (row: CrmAttributionTotals) => [
    [label("placed"), String(row.placed_orders)], [label("placedValue"), money(row.placed_revenue)],
    [label("active"), String(row.active_orders)], [label("activeValue"), money(row.active_revenue)],
    [label("cancelled"), String(row.cancelled_orders)], [label("returned"), String(row.returned_refunded_orders)],
    [label("fulfilled"), String(row.fulfilled_orders)], [label("fulfilledRevenue"), money(row.fulfilled_revenue)],
    [label("paid"), String(row.paid_fulfilled_orders)], [label("paidRevenue"), money(row.paid_fulfilled_revenue)],
    [label("declaredOrders"), String(row.metric_declared_orders)], [label("declaredRevenue"), money(row.metric_declared_revenue)],
  ];
  const rows = data ? [...data.campaigns.map((row) => ({ ...row, key: row.campaign_id, name: row.campaign_name, archived: row.campaign_status === "ARCHIVED", unknown: false })), ...(data.unattributed_orders > 0 ? [{ ...data.unattributed, key: "unattributed", name: label("unknown"), archived: false, unknown: true }] : [])] : [];
  return <section className="grid min-w-0 gap-4 rounded-2xl border border-border-subtle bg-surface-1 p-4 text-text-primary" data-crm-attribution>
    <div><h2 className="text-xl font-black">{label("title")}</h2><p className="mt-1 text-sm text-text-secondary">{label("intro")}</p></div>
    {invalid ? <p role="alert">{label("invalidDates")}</p> : report.isPending ? <p role="status">{label("loading")}</p> : report.isError ? <div role="alert"><p>{label("error")}</p><button type="button" className="mt-2 min-h-11 rounded-xl border border-border-subtle px-4 font-bold" onClick={() => report.refetch()}>{label("retry")}</button></div> : data ? <>
      <p className="text-sm font-semibold">{label("period")}: <time>{data.start_date}</time> — <time>{data.end_date}</time></p>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" data-crm-totals>
        {[[label("placed"), data.totals.placed_orders], [label("fulfilledRevenue"), money(data.totals.fulfilled_revenue)], [label("paidRevenue"), money(data.totals.paid_fulfilled_revenue)], [label("spend"), money(data.totals.spend)], [label("ratio"), data.totals.crm_period_revenue_to_spend ?? "—"], [label("cost"), money(data.totals.cost_per_fulfilled_order)]].map(([name, value]) => <div key={name} className="min-w-0 rounded-xl bg-surface-2 p-3"><p className="text-xs text-text-secondary">{name}</p><p className="mt-1 break-words text-lg font-black">{value}</p></div>)}
      </div>
      <p className="text-sm" data-crm-coverage>{label("coverage")}: <strong>{data.attribution_coverage_percent === null ? "—" : `${data.attribution_coverage_percent}%`}</strong> · {label("attributed")}: {data.attributed_orders} · {label("unknown")}: {data.unattributed_orders}</p>
      <p className="text-sm text-text-secondary">{label("ratioNote")}</p>
      <details className="rounded-xl border border-border-subtle p-3"><summary className="cursor-pointer font-semibold">{label("placed")} / {label("active")}</summary><dl className="mt-3 grid gap-2 sm:grid-cols-2">{stats(data.totals).map(([name, value]) => <div key={name} className="flex min-w-0 justify-between gap-3 text-sm"><dt>{name}</dt><dd className="shrink-0 font-bold">{value}</dd></div>)}</dl></details>
      {rows.length === 0 ? <p data-crm-empty>{label("empty")}</p> : <>
        <div className="grid gap-3 lg:hidden" data-crm-mobile>{rows.map((row) => <article key={row.key} className="min-w-0 rounded-xl border border-border-subtle p-3">
          <h3 className="break-words font-bold">{row.name}{row.archived ? ` · ${label("archived")}` : ""}</h3>
          <dl className="mt-3 grid gap-2">{[[label("fulfilled"), row.fulfilled_orders], [label("fulfilledRevenue"), money(row.fulfilled_revenue)], [label("paidRevenue"), money(row.paid_fulfilled_revenue)], [label("spend"), row.unknown ? "—" : money(row.spend)], [label("ratio"), row.crm_period_revenue_to_spend ?? "—"], [label("cost"), row.unknown ? "—" : money(row.cost_per_fulfilled_order)]].map(([name, value]) => <div key={name} className="flex justify-between gap-3 text-sm"><dt>{name}</dt><dd className="shrink-0 font-bold">{value}</dd></div>)}</dl>
          <details className="mt-3"><summary className="cursor-pointer text-sm font-semibold">{label("placed")} / {label("declared")}</summary><dl className="mt-2 grid gap-2">{stats(row).map(([name, value]) => <div key={name} className="flex justify-between gap-3 text-sm"><dt>{name}</dt><dd className="shrink-0 font-bold">{value}</dd></div>)}</dl></details>
        </article>)}</div>
        <div className="hidden min-w-0 overflow-x-auto lg:block" data-crm-desktop><table className="w-full text-left text-sm"><thead><tr>{["campaign", "placed", "fulfilledRevenue", "paidRevenue", "spend", "ratio", "declared"].map((key) => <th key={key} className="p-2 align-top">{label(key)}</th>)}</tr></thead><tbody>{rows.map((row) => <tr key={row.key} className="border-t border-border-subtle">
          <th scope="row" className="max-w-48 break-words p-2 align-top font-semibold">{row.name}{row.archived ? <span className="block text-xs text-text-secondary">{label("archived")}</span> : null}</th>
          <td className="p-2 align-top"><details><summary className="cursor-pointer">{row.placed_orders}</summary><dl className="mt-2 grid gap-2">{stats(row).slice(1, 6).map(([name, value]) => <div key={name}><dt className="text-xs text-text-secondary">{name}</dt><dd>{value}</dd></div>)}</dl></details></td>
          <td className="p-2 align-top">{money(row.fulfilled_revenue)}<span className="block text-xs text-text-secondary">{label("fulfilled")}: {row.fulfilled_orders}</span></td>
          <td className="p-2 align-top">{money(row.paid_fulfilled_revenue)}<span className="block text-xs text-text-secondary">{label("paid")}: {row.paid_fulfilled_orders}</span></td>
          <td className="p-2 align-top">{row.unknown ? "—" : money(row.spend)}</td>
          <td className="p-2 align-top">{row.crm_period_revenue_to_spend ?? "—"}<span className="block text-xs text-text-secondary">{label("cost")}: {row.unknown ? "—" : money(row.cost_per_fulfilled_order)}</span></td>
          <td className="p-2 align-top">{row.metric_declared_orders}<span className="block text-xs text-text-secondary">{money(row.metric_declared_revenue)}</span></td>
        </tr>)}</tbody></table></div>
      </>}
      {data.unattributed_orders > 0 ? <p className="text-sm text-text-secondary">{label("unknownHelp")}</p> : null}
    </> : null}
    <a href="/orders" className="w-fit min-h-11 rounded-xl border border-border-subtle px-4 py-3 text-sm font-bold">{label("assign")}</a>
  </section>;
}
