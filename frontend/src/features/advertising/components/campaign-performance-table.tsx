"use client";

import { CampaignPerformance } from "@/types/advertising";
import { MetricValue } from "./metric-value";
import { useI18n } from "@/i18n/provider";

export function CampaignPerformanceTable({ rows }: { rows: CampaignPerformance[] }) {
  const { t } = useI18n();
  return (
    <section className="w-full min-w-0 max-w-full overflow-hidden rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm">
      <h2 className="text-lg font-semibold text-text-primary">Ефективність кампаній</h2>
      <div className="sellora-scrollbar mt-3 max-w-full overflow-x-auto">
        <table className="w-full min-w-[920px] text-left text-sm">
          <thead><tr className="border-b border-border-subtle text-text-muted"><th>{t("advertising.campaign")}</th><th>{t("advertising.platform")}</th><th>{t("advertising.spend")}</th><th>{t("advertising.revenue")}</th><th>{t("advertising.orders")}</th><th>{t("advertising.leads")}</th><th>{t("advertising.messages")}</th><th>CPA</th><th>CPL</th><th>ROAS</th><th>{t("finance.netProfit")}</th><th>ROI</th></tr></thead>
          <tbody>{rows.map((row) => <tr key={row.campaign_id} className="border-b border-border-subtle last:border-0 hover:bg-surface-hover"><td className="py-2 font-medium text-text-primary">{row.campaign_name}</td><td>{row.platform}</td><td>{row.spend}</td><td>{row.revenue}</td><td>{row.orders}</td><td>{row.leads}</td><td>{row.messages}</td><td><MetricValue value={row.cpa} /></td><td><MetricValue value={row.cpl} /></td><td><MetricValue value={row.roas} /></td><td><MetricValue value={row.net_profit} /></td><td><MetricValue value={row.roi} suffix="%" /></td></tr>)}</tbody>
        </table>
      </div>
    </section>
  );
}
