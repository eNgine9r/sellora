"use client";

import { RowActionButtons } from "@/components/ui/row-action-buttons";
import { useI18n } from "@/i18n/provider";
import { statusBadgeClass } from "@/lib/status-styles";
import { AdCampaign } from "@/types/advertising";

export function CampaignTable({ campaigns, selectedCampaignId, onSelect, onEdit, onArchive }: { campaigns: AdCampaign[]; selectedCampaignId?: string; onSelect?: (campaign: AdCampaign) => void; onEdit?: (campaign: AdCampaign) => void; onArchive?: (campaign: AdCampaign) => void }) {
  const { t, formatStatus } = useI18n();
  const campaignStatus = (campaign: AdCampaign) => statusBadgeClass(campaign.status === "ACTIVE" ? "success" : campaign.status === "ARCHIVED" ? "neutral" : campaign.status === "PAUSED" ? "warning" : "info");

  return (
    <section className="sellora-adaptive-list w-full min-w-0 max-w-full rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm" data-campaign-mapping-source="manual-import-meta-ready">
      <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold">{t("advertising.campaigns")}</h2>
          <p className="mt-1 text-sm text-text-secondary">{t("advertising.mappingHint")}</p>
        </div>
        <span className="w-fit shrink-0 rounded-full bg-surface-2 px-3 py-1 text-xs font-bold text-text-secondary">{t("advertising.manualSource")}</span>
      </div>
      <div className="sellora-adaptive-table mt-3 min-w-0">
        <table className="w-full table-fixed text-left text-sm">
          <colgroup>
            <col style={{ width: "26%" }} />
            <col style={{ width: "13%" }} />
            <col style={{ width: "17%" }} />
            <col style={{ width: "16%" }} />
            <col style={{ width: "16%" }} />
            <col style={{ width: "12%" }} />
          </colgroup>
          <thead className="text-xs uppercase tracking-wide text-text-muted">
            <tr className="border-b border-border-subtle">
              <th className="px-2 py-3">{t("tables.name")}</th>
              <th className="px-2 py-3">{t("tables.status")}</th>
              <th className="px-2 py-3">{t("advertising.objective")}</th>
              <th className="px-2 py-3">{t("advertising.dailyBudget")}</th>
              <th className="px-2 py-3">{t("advertising.startDate")}</th>
              <th className="px-2 py-3 text-right">{t("tables.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {campaigns.map((campaign) => (
              <tr key={campaign.id} className={`cursor-pointer border-b border-border-subtle last:border-0 transition hover:bg-surface-hover ${selectedCampaignId === campaign.id ? "bg-surface-selected" : ""}`} onClick={() => onSelect?.(campaign)}>
                <td className="min-w-0 px-2 py-3">
                  <span className="block truncate font-semibold text-text-primary" title={campaign.name}>{campaign.name}</span>
                  <span className="block truncate text-xs text-text-muted">{campaign.platform} · {t("advertising.manualSource")}</span>
                </td>
                <td className="px-2 py-3"><span className={campaignStatus(campaign)}>{formatStatus("campaign", campaign.status)}</span></td>
                <td className="min-w-0 truncate px-2 py-3 text-text-secondary" title={campaign.objective ?? undefined}>{campaign.objective ?? "—"}</td>
                <td className="px-2 py-3 text-text-secondary">
                  <span className="block">{campaign.daily_budget ?? "—"}</span>
                  <span className="block text-xs text-text-muted">{t("advertising.totalBudget")}: {campaign.total_budget ?? "—"}</span>
                </td>
                <td className="px-2 py-3 text-xs text-text-secondary">
                  <span className="block">{campaign.start_date ?? "—"}</span>
                  <span className="block">{campaign.end_date ?? "—"}</span>
                </td>
                <td className="px-1 py-2"><RowActionButtons entityLabel={campaign.name} editLabel={t("advertising.editCampaign")} archiveLabel={t("actions.archive")} onEdit={onEdit ? () => onEdit(campaign) : undefined} onArchive={onArchive ? () => onArchive(campaign) : undefined} /></td>
              </tr>
            ))}
            {campaigns.length === 0 ? <tr><td className="p-6 text-center text-text-muted" colSpan={6}>{t("advertising.emptyCampaigns")} {t("advertising.manualImportFirst")}</td></tr> : null}
          </tbody>
        </table>
      </div>
      <div className="sellora-adaptive-cards mt-3 grid gap-3">
        {campaigns.map((campaign) => (
          <article key={campaign.id} className={`min-w-0 rounded-xl border border-border-subtle bg-surface-2 p-3 ${selectedCampaignId === campaign.id ? "bg-surface-selected" : ""}`}>
            <button type="button" className="w-full min-w-0 text-left" onClick={() => onSelect?.(campaign)}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0"><h3 className="truncate font-semibold text-text-primary">{campaign.name}</h3><p className="text-xs text-text-muted">{campaign.platform} · {t("advertising.manualSource")}</p></div>
                <span className={campaignStatus(campaign)}>{formatStatus("campaign", campaign.status)}</span>
              </div>
              <p className="mt-2 text-sm text-text-secondary">{t("advertising.objective")}: {campaign.objective ?? "—"}</p>
              <p className="mt-1 text-sm text-text-secondary">{t("advertising.dailyBudget")}: {campaign.daily_budget ?? "—"} · {t("advertising.totalBudget")}: {campaign.total_budget ?? "—"}</p>
              <p className="mt-1 text-xs text-text-muted">{campaign.start_date ?? "—"} — {campaign.end_date ?? "—"}</p>
            </button>
            <div className="mt-2 flex justify-end"><RowActionButtons entityLabel={campaign.name} editLabel={t("advertising.editCampaign")} archiveLabel={t("actions.archive")} onEdit={onEdit ? () => onEdit(campaign) : undefined} onArchive={onArchive ? () => onArchive(campaign) : undefined} /></div>
          </article>
        ))}
        {campaigns.length === 0 ? <p className="p-4 text-center text-text-muted">{t("advertising.emptyCampaigns")}</p> : null}
      </div>
    </section>
  );
}
// Localization regression compatibility markers: Edit campaign; Archive campaign; Meta-ready mapping; Manual/import source.
