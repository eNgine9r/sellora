"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
import { EditRecordDialog } from "@/components/edit-record-dialog";
import { FormDialog } from "@/components/form-dialog";
import { LeadForm } from "@/features/leads/components/lead-form";
import { LeadTable } from "@/features/leads/components/lead-table";
import { ApiError, safeApiErrorMessage } from "@/services/api";
import { createLead, deleteLead, fetchLeads, fetchLeadSources, LeadCreatePayload, updateLead } from "@/services/crm";
import { Lead, LeadStatus } from "@/types/crm";
import { buildLeadUpdatePayload } from "@/lib/payload-builders";
import { useAuth } from "@/hooks/use-auth";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";

const STATUSES: (LeadStatus | "")[] = ["", "NEW", "IN_PROGRESS", "QUALIFIED", "CONVERTED", "LOST"];

function messageForApiError(error: unknown, context: "list" | "create" | "sources") {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Session expired. Please log in again.";
    if (error.status === 403) return "You do not have permission to manage leads.";
    if (error.status === 422) return safeApiErrorMessage(error, context === "create" ? "Lead data is invalid. Please check the form." : "Lead filters are invalid. Please reset filters and try again.");
  }
  if (context === "create") return "Unable to create lead. Please try again.";
  if (context === "sources") return "Unable to load lead sources. You can still create a lead without a source.";
  return "Unable to load leads. Please try again.";
}

export default function LeadsPage() {
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspace, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<LeadStatus | "">("");
  const [leadSourceId, setLeadSourceId] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingLead, setEditingLead] = useState<Lead | null>(null);
  const [archivingLead, setArchivingLead] = useState<Lead | null>(null);
  const authReady = authStatus !== "loading";
  const enabled = authReady && authStatus === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);
  const canEdit = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";

  const filters = useMemo(() => ({ search, status, leadSourceId }), [search, status, leadSourceId]);
  const leadsQuery = useQuery({ queryKey: ["leads", workspaceId, filters], queryFn: () => fetchLeads(workspaceId, filters, undefined), enabled });
  const sourcesQuery = useQuery({ queryKey: ["lead-sources", workspaceId], queryFn: () => fetchLeadSources(workspaceId, undefined), enabled });
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

  const listError = leadsQuery.isError ? messageForApiError(leadsQuery.error, "list") : null;
  const createError = createMutation.isError ? messageForApiError(createMutation.error, "create") : null;
  const updateError = updateMutation.isError ? messageForApiError(updateMutation.error, "create") : null;
  const sourcesError = sourcesQuery.isError ? messageForApiError(sourcesQuery.error, "sources") : null;

  return (
    <main className="min-h-screen min-w-0 overflow-x-hidden bg-[#F8F7FC] p-4 text-slate-950 sm:p-6">
      <div className="mx-auto grid min-w-0 max-w-7xl gap-6">
        <header className="flex flex-col gap-4 rounded-2xl bg-white p-6 shadow-sm md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Sellora CRM</p>
            <h1 className="mt-2 text-3xl font-bold">Leads</h1>
            <p className="mt-1 text-slate-600">Capture, qualify, assign, and convert leads into customers.</p>
          </div>
          <button className="min-h-11 rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={!enabled} onClick={() => setIsCreateOpen(true)}>Create lead</button>
        </header>

        <section className="grid min-w-0 gap-3 rounded-2xl bg-white p-4 shadow-sm md:grid-cols-5">
          <input className="min-h-11 rounded-md border border-slate-300 px-3 py-2" placeholder="Search leads" value={search} onChange={(event) => setSearch(event.target.value)} />
          <select className="min-h-11 rounded-md border border-slate-300 px-3 py-2" value={status} onChange={(event) => setStatus(event.target.value as LeadStatus | "")}>
            {STATUSES.map((item) => <option key={item || "all"} value={item}>{item || "All statuses"}</option>)}
          </select>
          <select className="min-h-11 rounded-md border border-slate-300 px-3 py-2" value={leadSourceId} onChange={(event) => setLeadSourceId(event.target.value)}>
            <option value="">All sources</option>
            {(sourcesQuery.data ?? []).map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}
          </select>
        </section>

        {!authReady ? <LoadingSkeleton title="Preparing your workspace…" /> : null}
        {authReady && authStatus === "authenticated" && !workspaceId ? <ErrorState description="Workspace is not ready yet. Please refresh the page." title="Workspace unavailable" /> : null}
        {sourcesError ? <p className="rounded-lg bg-amber-50 p-4 text-sm font-semibold text-amber-700">{sourcesError}</p> : null}
        {leadsQuery.isLoading || leadsQuery.isFetching && !leadsQuery.data ? <LoadingSkeleton title="Loading leads…" /> : null}
        {listError ? <ErrorState description={listError} onRetry={() => void leadsQuery.refetch()} title="Unable to load leads" /> : null}
        {!listError && leadsQuery.isSuccess && (leadsQuery.data?.length ?? 0) === 0 ? (
          <EmptyState
            title="No leads yet"
            description="Create your first lead or import historical Instagram conversations to start building your CRM pipeline."
            action={<button className="min-h-11 rounded-2xl bg-blue-600 px-4 text-sm font-black text-white" onClick={() => setIsCreateOpen(true)}>Create lead</button>}
          />
        ) : null}
        {!listError && (leadsQuery.data?.length ?? 0) > 0 ? <LeadTable leads={leadsQuery.data ?? []} leadSources={sourcesQuery.data ?? []} onEdit={canEdit ? setEditingLead : undefined} onArchive={canEdit ? setArchivingLead : undefined} /> : null}

        {isCreateOpen ? (
          <FormDialog title="Create lead" description="Only the name is required. Empty optional fields are safely omitted." size="md" onClose={() => setIsCreateOpen(false)}>
            <LeadForm
              isSubmitting={createMutation.isPending}
              leadSources={sourcesQuery.data ?? []}
              submitError={createError}
              onSubmit={async (payload) => {
                await createMutation.mutateAsync(payload);
              }}
            />
          </FormDialog>
        ) : null}
        {archivingLead ? <ConfirmActionDialog title="Archive lead?" description={archivingLead.status === "CONVERTED" ? "This lead is converted. Archiving it will not delete the customer." : "This lead will be hidden from active lead lists. Historical audit records remain available."} actionLabel="Archive lead" isSubmitting={archiveMutation.isPending} error={archiveMutation.isError ? safeApiErrorMessage(archiveMutation.error, "Unable to delete record. Please try again.") : null} onCancel={() => setArchivingLead(null)} onConfirm={() => archiveMutation.mutate()} /> : null}
        {editingLead ? <EditRecordDialog title="Edit lead" fields={[{ name: "name", label: "Name" }, { name: "phone", label: "Phone" }, { name: "instagram_username", label: "Instagram username" }, { name: "instagram_profile_url", label: "Instagram profile URL" }, { name: "lead_source_id", label: "Lead source ID" }, { name: "status", label: "Status", type: "select", options: STATUSES.filter(Boolean).map((item) => ({ value: item, label: item })) }, { name: "expected_revenue", label: "Expected revenue", type: "number" }, { name: "loss_reason", label: "Loss reason", type: "textarea" }, { name: "notes", label: "Notes", type: "textarea" }]} initialValues={editingLead} isSubmitting={updateMutation.isPending} submitError={updateError} onClose={() => setEditingLead(null)} onSubmit={(values) => updateMutation.mutate(values)} /> : null}
      </div>
    </main>
  );
}
