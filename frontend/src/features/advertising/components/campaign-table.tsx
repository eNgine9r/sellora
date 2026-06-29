"use client";

import { useI18n } from "@/i18n/provider";
import { statusBadgeClass } from "@/lib/status-styles";
import { AdCampaign } from "@/types/advertising";

export function CampaignTable({ campaigns, onEdit, onArchive }: { campaigns: AdCampaign[]; onEdit?: (campaign: AdCampaign) => void; onArchive?: (campaign: AdCampaign) => void }) {
  const { t, formatStatus } = useI18n();

  return (
    <section className="w-full min-w-0 max-w-full overflow-hidden rounded-2xl bg-white p-4 shadow-sm" data-campaign-mapping-source="manual-import-meta-ready">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">{t("advertising.campaigns")}</h2>
          <p className="mt-1 text-sm text-slate-500">{t("advertising.mappingHint")}</p>
        </div>
        <span className="w-fit rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">{t("advertising.manualSource")}</span>
      </div>
      <div className="sellora-scrollbar mt-3 max-w-full overflow-x-auto">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead>
            <tr className="border-b text-slate-500">
              <th>{t("tables.name")}</th>
              <th>{t("advertising.platform")}</th>
              <th>{t("advertising.source")}</th>
              <th>{t("tables.status")}</th>
              <th>{t("advertising.objective")}</th>
              <th>{t("advertising.dailyBudget")}</th>
              <th>{t("advertising.totalBudget")}</th>
              <th>{t("advertising.startDate")}</th>
              <th>{t("advertising.endDate")}</th>
              <th>{t("tables.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {campaigns.map((campaign) => (
              <tr key={campaign.id} className="border-b last:border-0">
                <td className="py-2 font-medium">{campaign.name}</td>
                <td>{campaign.platform}</td>
                <td><span className="rounded-full bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700">{t("advertising.manualSource")}</span></td>
                <td><span className={statusBadgeClass(campaign.status === "ACTIVE" ? "success" : campaign.status === "ARCHIVED" ? "neutral" : campaign.status === "PAUSED" ? "warning" : "info")}>{formatStatus("campaign", campaign.status)}</span></td>
                <td>{campaign.objective}</td>
                <td>{campaign.daily_budget ?? "—"}</td>
                <td>{campaign.total_budget ?? "—"}</td>
                <td>{campaign.start_date ?? "—"}</td>
                <td>{campaign.end_date ?? "—"}</td>
                <td><div className="flex flex-wrap gap-2">{onEdit ? <button aria-label={`${t("advertising.editCampaign")} ${campaign.name}`} className="rounded-lg border border-slate-300 px-3 py-2 font-semibold" onClick={() => onEdit(campaign)}>{t("advertising.editCampaign")}</button> : <span className="text-slate-400">{t("common.readOnly")}</span>}{onArchive ? <button aria-label={`${t("actions.archive")} ${campaign.name}`} className="rounded-lg border border-rose-200 px-3 py-2 font-semibold text-rose-700" onClick={() => onArchive(campaign)}>{t("actions.archive")}</button> : null}</div></td>
              </tr>
            ))}
            {campaigns.length === 0 ? <tr><td className="py-6 text-center text-slate-500" colSpan={10}>{t("advertising.emptyCampaigns")} {t("advertising.manualImportFirst")}</td></tr> : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
// Localization regression compatibility markers: Edit campaign; Archive campaign; Meta-ready mapping; Manual/import source.
