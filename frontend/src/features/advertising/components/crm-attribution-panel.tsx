"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Link2Off, Receipt, ShieldCheck } from "lucide-react";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import { fetchCrmAttribution } from "@/services/advertising";

export function CrmAttributionPanel({
  workspaceId, startDate, endDate, currencyCode, enabled,
}: {
  workspaceId: string; startDate: string; endDate: string;
  currencyCode: string; enabled: boolean;
}) {
  const { t } = useI18n();
  const validPeriod = Boolean(startDate && endDate && startDate <= endDate);
  const report = useQuery({
    queryKey: ["ad-crm-attribution", workspaceId, startDate, endDate],
    queryFn: () => fetchCrmAttribution(workspaceId, startDate, endDate),
    enabled: enabled && validPeriod,
    retry: false,
  });

  return (
    <section className="grid min-w-0 gap-4 rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm sm:p-5"
      data-advertising-crm-attribution aria-label={t("adsDashboard.crmAttributionTitle")}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="size-5 text-indigo-500" aria-hidden="true" />
            <h2 className="text-base font-bold text-text-primary">{t("adsDashboard.crmAttributionTitle")}</h2>
          </div>
          <p className="mt-1 text-xs leading-5 text-text-secondary">{t("adsDashboard.crmAttributionSubtitle")}</p>
        </div>
        <span className="rounded-full border border-border-subtle px-2.5 py-1 text-xs font-medium text-text-secondary">{t("adsDashboard.crmAttributionSource")}</span>
      </div>
      {report.isLoading ? <p role="status" className="text-sm text-text-secondary">{t("common.loading")}</p> : null}
      {report.isError ? <p role="alert" className="text-sm text-rose-500">{t("adsDashboard.crmAttributionError")}</p> : null}
      {report.data ? (
        <>
          <div className="grid min-w-0 gap-3 sm:grid-cols-3">
            <div className="rounded-xl bg-surface-2 p-4">
              <p className="text-xs text-text-secondary">{t("adsDashboard.crmLinkedOrders")}</p>
              <p className="mt-2 text-2xl font-bold tabular-nums text-text-primary">{report.data.linked_orders.toLocaleString()}</p>
              <p className="mt-1 text-xs text-text-muted">{t("adsDashboard.crmLinkedCaption")}</p>
            </div>
            <div className="rounded-xl bg-surface-2 p-4">
              <p className="text-xs text-text-secondary">{t("adsDashboard.crmPaidCompletedRevenue")}</p>
              <p className="mt-2 truncate text-2xl font-bold tabular-nums text-text-primary">{formatMoney(report.data.completed_paid_revenue, currencyCode)}</p>
              <p className="mt-1 text-xs text-text-muted">{report.data.completed_paid_orders} {t("adsDashboard.crmPaidOrders")}</p>
            </div>
            <div className="rounded-xl bg-surface-2 p-4">
              <div className="flex items-center gap-2 text-xs text-text-secondary"><Link2Off className="size-4" aria-hidden="true" />{t("adsDashboard.crmUnattributed")}</div>
              <p className="mt-2 text-2xl font-bold tabular-nums text-text-primary">{report.data.unattributed_completed_paid_orders.toLocaleString()}</p>
              <p className="mt-1 text-xs text-text-muted">{t("adsDashboard.crmUnattributedCaption")}</p>
            </div>
          </div>
          {report.data.campaigns.length ? (
            <div className="grid gap-2">
              <p className="text-xs font-semibold text-text-secondary">{t("adsDashboard.crmLinkedCampaigns")}</p>
              {report.data.campaigns.map(row => (
                <div key={row.campaign_id} className="flex min-w-0 items-center justify-between gap-3 border-t border-border-subtle py-2 text-sm">
                  <span className="min-w-0 truncate text-text-primary" title={row.campaign_name}>{row.campaign_name}</span>
                  <span className="shrink-0 tabular-nums text-text-secondary">{row.linked_orders} {t("adsDashboard.crmOrdersShort")}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center gap-2 rounded-xl border border-dashed border-border-subtle p-3 text-sm text-text-secondary">
              <Receipt className="size-4 shrink-0" aria-hidden="true" />
              {t("adsDashboard.crmEmpty")}
            </div>
          )}
          <div className="flex items-start gap-2 border-t border-border-subtle pt-3 text-xs leading-5 text-text-muted">
            <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-indigo-500" aria-hidden="true" />
            <span>{t("adsDashboard.crmTruthNotice")}</span>
          </div>
        </>
      ) : null}
    </section>
  );
}
