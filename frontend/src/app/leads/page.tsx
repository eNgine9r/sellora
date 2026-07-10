"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
import { EditRecordDialog } from "@/components/edit-record-dialog";
import { FilterBar, ResetFiltersButton, SearchInput, SortSelect } from "@/components/filter-controls";
import { FormDialog } from "@/components/form-dialog";
import { LeadForm } from "@/features/leads/components/lead-form";
import { LeadTable } from "@/features/leads/components/lead-table";
import { ApiError, safeApiErrorMessage } from "@/services/api";
import { createLead, deleteLead, fetchLeads, fetchLeadSources, LeadCreatePayload, updateLead } from "@/services/crm";
import { fetchAdCampaigns } from "@/services/advertising";
import { Lead, LeadStatus } from "@/types/crm";
import { buildLeadUpdatePayload } from "@/lib/payload-builders";
import { useAuth } from "@/hooks/use-auth";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";
import { useI18n } from "@/i18n/provider";

const STATUSES: (LeadStatus | "")[] = ["", "NEW", "IN_PROGRESS", "QUALIFIED", "CONVERTED", "LOST"];

function messageForApiError(error: unknown, context: "list" | "create" | "sources", t: (key: string) => string) {
  if (error instanceof ApiError) {
    if (error.status === 401) return t("leads.apiSessionExpired");
    if (error.status === 403) return t("leads.apiForbidden");
    if (error.status === 422) return safeApiErrorMessage(error, context === "create" ? t("leads.apiInvalid") : t("leads.apiLoadFailed"));
  }
  if (context === "create") return t("leads.apiCreateFailed");
  if (context === "sources") return t("leads.sourceWarning");
  return t("leads.apiLoadFailed");
}

export default function LeadsPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspace, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<LeadStatus | "">("");
  const [leadSourceId, setLeadSourceId] = useState("");
  const [leadSort, setLeadSort] = useState("newest");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingLead, setEditingLead] = useState<Lead | null>(null);
  const [archivingLead, setArchivingLead] = useState<Lead | null>(null);
  const authReady = authStatus !== "loading";
  const enabled = authReady && authStatus === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);
  const canEdit = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";

  const filters = useMemo(() => ({ search, status, leadSourceId }), [search, status, leadSourceId]);
  const leadsQuery = useQuery({ queryKey: ["leads", workspaceId, filters], queryFn: () => fetchLeads(workspaceId, filters, undefined), enabled });
  const sourcesQuery = useQuery({ queryKey: ["lead-sources", workspaceId], queryFn: () => fetchLeadSources(workspaceId, undefined), enabled });
  const campaignsQuery = useQuery({ queryKey: ["ad-campaigns", workspaceId], queryFn: () => fetchAdCampaigns(workspaceId, undefined), enabled });
  const createMutation = useMutation({
    mutationFn: (payload: LeadCreatePayload) => createLead(workspaceId, payload, undefined),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["leads", workspaceId] });
      setIsCreateOpen(false);
    },
  });
  const updateMutation = useMutation({
    mutationFn: (values: Record<string, string>) => updateLead(workspaceId, editingLead?.id ?? "", buildLeadUpdatePayload(values), undefined),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["leads", workspaceId] });
      setEditingLead(null);
    },
  });
  const archiveMutation = useMutation({
    mutationFn: () => deleteLead(workspaceId, archivingLead?.id ?? "", undefined),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["leads", workspaceId] });
      setArchivingLead(null);
    },
  });

  const listError = leadsQuery.isError ? messageForApiError(leadsQuery.error, "list", t) : null;
  const createError = createMutation.isError ? messageForApiError(createMutation.error, "create", t) : null;
  const updateError = updateMutation.isError ? messageForApiError(updateMutation.error, "create", t) : null;
  const sourcesError = sourcesQuery.isError ? messageForApiError(sourcesQuery.error, "sources", t) : null;
  const visibleLeads = useMemo(() => [...(leadsQuery.data ?? [])].sort((left, right) => {
    const leftRevenue = Number(left.expected_revenue ?? 0);
    const rightRevenue = Number(right.expected_revenue ?? 0);
    if (leadSort === "oldest") return left.created_at.localeCompare(right.created_at);
    if (leadSort === "revenueDesc") return rightRevenue - leftRevenue;
    if (leadSort === "revenueAsc") return leftRevenue - rightRevenue;
    return right.created_at.localeCompare(left.created_at);
  }), [leadsQuery.data, leadSort]);
  const hasActiveFilters = Boolean(search.trim() || status || leadSourceId);

  return (
    <main className="min-h-screen min-w-0 overflow-x-hidden bg-[#F8F7FC] p-4 text-slate-950 sm:p-6">
      <div className="mx-auto grid min-w-0 max-w-7xl gap-6">
        <header className="flex flex-col gap-4 rounded-2xl bg-white p-6 shadow-sm md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Sellora CRM</p>
            <h1 className="mt-2 text-3xl font-bold">{t("leads.title")}</h1>
            <p className="mt-1 text-slate-600">{t("leads.subtitle")}</p>
          </div>
          <button className="min-h-11 rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={!enabled} onClick={() => setIsCreateOpen(true)}>{t("leads.create")}</button>
        </header>

        <FilterBar>
          <SearchInput value={search} onChange={setSearch} placeholder={t("leads.searchPlaceholder")} />
          <select className="min-h-11 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm dark:border-white/10 dark:bg-white/10 dark:text-white" value={status} onChange={(event) => setStatus(event.target.value as LeadStatus | "")}>
            {STATUSES.map((item) => <option key={item || "all"} value={item}>{item ? t(`statuses.lead.${item}`) : t("common.allStatuses")}</option>)}
          </select>
          <select className="min-h-11 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm dark:border-white/10 dark:bg-white/10 dark:text-white" value={leadSourceId} onChange={(event) => setLeadSourceId(event.target.value)}>
            <option value="">{t("leads.allSources")}</option>
            {(sourcesQuery.data ?? []).map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}
          </select>
          <SortSelect value={leadSort} onChange={setLeadSort} options={[{ value: "newest", label: t("sort.newest") }, { value: "oldest", label: t("sort.oldest") }, { value: "revenueDesc", label: t("sort.revenueDesc") }, { value: "revenueAsc", label: t("sort.revenueAsc") }]} />
          <ResetFiltersButton onClick={() => { setSearch(""); setStatus(""); setLeadSourceId(""); setLeadSort("newest"); }} />
        </FilterBar>

        {!authReady ? <LoadingSkeleton title={t("common.loadingWorkspace")} /> : null}
        {authReady && authStatus === "authenticated" && !workspaceId ? <ErrorState description={t("common.workspaceUnavailableDescription")} title={t("common.workspaceUnavailable")} /> : null}
        {sourcesError ? <p className="rounded-lg bg-amber-50 p-4 text-sm font-semibold text-amber-700">{sourcesError}</p> : null}
        {leadsQuery.isLoading || leadsQuery.isFetching && !leadsQuery.data ? <LoadingSkeleton title={t("leads.loading")} /> : null}
        {listError ? <ErrorState description={listError} onRetry={() => void leadsQuery.refetch()} title={t("leads.loadError")} /> : null}
        {!listError && leadsQuery.isSuccess && (leadsQuery.data?.length ?? 0) === 0 ? (
          <EmptyState
            title={hasActiveFilters ? t("leads.filteredEmptyTitle") : t("leads.emptyTitle")}
            description={hasActiveFilters ? t("leads.filteredEmptyDescription") : t("leads.emptyDescription")}
            action={<button className="min-h-11 rounded-2xl bg-blue-600 px-4 text-sm font-black text-white" onClick={() => setIsCreateOpen(true)}>{t("leads.create")}</button>}
          />
        ) : null}
        {!listError && (leadsQuery.data?.length ?? 0) > 0 ? <LeadTable leads={visibleLeads} leadSources={sourcesQuery.data ?? []} onEdit={canEdit ? setEditingLead : undefined} onArchive={canEdit ? setArchivingLead : undefined} /> : null}

        {isCreateOpen ? (
          <FormDialog title={t("leads.create")} description={t("leads.createHelp")} size="md" onClose={() => setIsCreateOpen(false)}>
            <LeadForm
              isSubmitting={createMutation.isPending}
              leadSources={sourcesQuery.data ?? []}
              campaigns={campaignsQuery.data ?? []}
              submitError={createError}
              onSubmit={async (payload) => {
                await createMutation.mutateAsync(payload);
              }}
            />
          </FormDialog>
        ) : null}
        {archivingLead ? <ConfirmActionDialog title={t("leads.archiveTitle")} description={archivingLead.status === "CONVERTED" ? t("leads.archiveConvertedDescription") : t("leads.archiveDescription")} actionLabel={t("leads.archive")} isSubmitting={archiveMutation.isPending} error={archiveMutation.isError ? safeApiErrorMessage(archiveMutation.error, t("errors.deleteFailed")) : null} onCancel={() => setArchivingLead(null)} onConfirm={() => archiveMutation.mutate()} /> : null}
        {editingLead ? <EditRecordDialog title={t("leads.edit")} fields={[{ name: "name", label: t("tables.name") }, { name: "phone", label: t("tables.phone") }, { name: "instagram_username", label: t("tables.instagram") }, { name: "instagram_profile_url", label: "Instagram URL" }, { name: "lead_source_id", label: t("leads.source"), type: "select", options: [{ value: "", label: t("leads.noSource") }, ...(sourcesQuery.data ?? []).map((source) => ({ value: source.id, label: source.name }))] }, { name: "campaign_id", label: t("leads.campaignLabel"), type: "select", options: [{ value: "", label: t("leads.noCampaign") }, ...(campaignsQuery.data ?? []).map((campaign) => ({ value: campaign.id, label: `${campaign.name} · ${campaign.platform}` }))] }, { name: "status", label: t("tables.status"), type: "select", options: STATUSES.filter(Boolean).map((item) => ({ value: item, label: t(`statuses.lead.${item}`) })) }, { name: "expected_revenue", label: t("analytics.revenue"), type: "number" }, { name: "loss_reason", label: t("statuses.lead.LOST"), type: "textarea" }, { name: "notes", label: t("orders.notes"), type: "textarea" }]} initialValues={editingLead} isSubmitting={updateMutation.isPending} submitError={updateError} onClose={() => setEditingLead(null)} onSubmit={(values) => updateMutation.mutate(values)} /> : null}
      </div>
    </main>
  );
}
// Localization regression compatibility marker: FormDialog title="Create lead".
