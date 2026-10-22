import { Lead, LeadSource } from "@/types/crm";
import { RowActionButtons } from "@/components/ui/row-action-buttons";
import { useI18n } from "@/i18n/provider";
import { LeadStatusBadge } from "./lead-status-badge";

function nextActionKey(status: Lead["status"]) {
  if (status === "NEW" || status === "IN_PROGRESS") return "leads.nextActionContact";
  if (status === "QUALIFIED") return "leads.nextActionCreateOrder";
  if (status === "CONVERTED") return "leads.nextActionConverted";
  return "leads.nextActionLost";
}

export function LeadTable({ leads, leadSources, selectedLeadId, onSelect, onEdit, onArchive }: { leads: Lead[]; leadSources: LeadSource[]; selectedLeadId?: string | null; onSelect?: (lead: Lead) => void; onEdit?: (lead: Lead) => void; onArchive?: (lead: Lead) => void }) {
  const { t } = useI18n();
  const sourceById = new Map(leadSources.map((source) => [source.id, source.name]));
  const sourceName = (lead: Lead) => lead.lead_source_id ? sourceById.get(lead.lead_source_id) ?? t("leads.unknownSource") : "—";

  return <div className="sellora-adaptive-list mobile-card-list w-full min-w-0 max-w-full rounded-[var(--radius-card)] border border-border-subtle bg-surface-1 p-3 shadow-[var(--shadow-card)]">
    <div className="sellora-adaptive-table min-w-0 w-full">
      <table className="w-full table-fixed divide-y divide-border-subtle text-left text-sm">
        <colgroup>
          <col style={{ width: "23%" }} />
          <col style={{ width: "12%" }} />
          <col style={{ width: "19%" }} />
          <col style={{ width: "12%" }} />
          <col style={{ width: "15%" }} />
          <col style={{ width: "9%" }} />
          <col style={{ width: "10%" }} />
        </colgroup>
        <thead className="bg-surface-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
          <tr>
            <th className="px-2 py-3">{t("tables.name")}</th>
            <th className="px-2 py-3">{t("tables.status")}</th>
            <th className="px-2 py-3">{t("leads.source")}</th>
            <th className="px-2 py-3">{t("leads.assignedManager")}</th>
            <th className="px-2 py-3">{t("leads.nextAction")}</th>
            <th className="px-2 py-3">{t("leads.createdAt")}</th>
            <th className="px-2 py-3 text-right">{t("tables.actions")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border-subtle">
          {leads.map((lead) => (
            <tr key={lead.id} className={`cursor-pointer transition hover:bg-surface-hover ${selectedLeadId === lead.id ? "bg-surface-selected" : ""}`} onClick={() => onSelect?.(lead)}>
              <td className="min-w-0 px-2 py-3">
                <span className="block truncate font-semibold text-text-primary" title={lead.name}>{lead.name}</span>
                <span className="block truncate text-xs text-text-muted" title={lead.instagram_username ?? undefined}>{lead.instagram_username ? `@${lead.instagram_username.replace(/^@/, "")}` : "—"}</span>
                {lead.phone ? <span className="block truncate text-xs text-text-secondary">{lead.phone}</span> : null}
              </td>
              <td className="px-2 py-3"><LeadStatusBadge status={lead.status} /></td>
              <td className="min-w-0 px-2 py-3 text-text-secondary">
                <span className="block truncate" title={sourceName(lead)}>{sourceName(lead)}</span>
                <span className="block truncate text-xs text-text-muted" title={lead.campaign_name ?? undefined}>{lead.campaign_name ?? "—"}</span>
              </td>
              <td className="min-w-0 px-2 py-3 text-xs text-text-secondary">{lead.assigned_user_id ? t("leads.assigned") : t("leads.unassigned")}</td>
              <td className="px-2 py-3 text-xs leading-5 text-text-secondary">{t(nextActionKey(lead.status))}</td>
              <td className="px-2 py-3 text-xs text-text-secondary">{new Date(lead.created_at).toLocaleDateString("uk-UA")}</td>
              <td className="px-1 py-2">
                <RowActionButtons
                  entityLabel={lead.name}
                  editLabel={t("leads.edit")}
                  archiveLabel={t("leads.archive")}
                  onEdit={onEdit ? () => onEdit(lead) : undefined}
                  onArchive={onArchive ? () => onArchive(lead) : undefined}
                />
              </td>
            </tr>
          ))}
          {leads.length === 0 ? <tr><td colSpan={7} className="p-6 text-center text-text-muted">{t("leads.empty")}</td></tr> : null}
        </tbody>
      </table>
    </div>
    <div className="sellora-adaptive-cards grid gap-3">{leads.map((lead) => <article key={lead.id} onClick={() => onSelect?.(lead)} className="mobile-lead-card cursor-pointer min-w-0 rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-[var(--shadow-card)]"><div className="flex min-w-0 items-start justify-between gap-3"><div className="min-w-0"><p className="truncate text-sm font-bold text-primary">{lead.instagram_username ? `@${lead.instagram_username.replace(/^@/, "")}` : sourceName(lead)}</p><h3 className="mt-1 truncate text-lg font-black text-text-primary">{lead.name}</h3><p className="truncate text-sm text-text-muted">{t("tables.phone")}: {lead.phone ?? "—"}</p></div><LeadStatusBadge status={lead.status} /></div><div className="mt-3 grid gap-1 text-sm text-text-secondary"><span>{t("leads.source")}: {sourceName(lead)}</span><span>{t("leads.campaignLabel")}: {lead.campaign_name ?? "—"}</span><span>{t("leads.nextAction")}: {t(nextActionKey(lead.status))}</span><span>{t("leads.createdAt")}: {new Date(lead.created_at).toLocaleDateString()}</span></div><div className="mt-4 grid gap-2 sm:grid-cols-2">{onEdit ? <button aria-label={`${t("leads.edit")} ${lead.name}`} className="min-h-11 rounded-xl border border-border-subtle bg-surface-2 px-4 py-3 font-bold" onClick={(event) => { event.stopPropagation(); onEdit(lead); }}>{t("leads.edit")}</button> : <span className="text-sm text-slate-400">{t("common.readOnly")}</span>}{onArchive ? <button aria-label={`${t("leads.archive")} ${lead.name}`} className="min-h-11 rounded-xl border border-rose-200 px-4 py-3 font-bold text-rose-700 dark:border-rose-400/40 dark:text-rose-200" onClick={(event) => { event.stopPropagation(); onArchive(lead); }}>{t("leads.archive")}</button> : null}</div></article>)}{leads.length === 0 ? <p className="p-6 text-center text-slate-500">{t("leads.empty")}</p> : null}</div></div>;
}
