"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { LeadForm, LeadFormValues } from "@/features/leads/components/lead-form";
import { LeadTable } from "@/features/leads/components/lead-table";
import { createLead, fetchLeads, fetchLeadSources } from "@/services/crm";
import { LeadStatus } from "@/types/crm";
import { useAuth } from "@/hooks/use-auth";

const STATUSES: (LeadStatus | "")[] = ["", "NEW", "IN_PROGRESS", "QUALIFIED", "CONVERTED", "LOST"];

export default function LeadsPage() {
  const queryClient = useQueryClient();
  const { currentWorkspaceId } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<LeadStatus | "">("");
  const [leadSourceId, setLeadSourceId] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const enabled = Boolean(workspaceId);

  const filters = useMemo(() => ({ search, status, leadSourceId }), [search, status, leadSourceId]);
  const leadsQuery = useQuery({ queryKey: ["leads", workspaceId, filters], queryFn: () => fetchLeads(workspaceId, filters, undefined), enabled });
  const sourcesQuery = useQuery({ queryKey: ["lead-sources", workspaceId], queryFn: () => fetchLeadSources(workspaceId, undefined), enabled });
  const createMutation = useMutation({
    mutationFn: (values: LeadFormValues) => createLead(workspaceId, values, undefined),
    onSuccess: () => {
      setIsCreateOpen(false);
      queryClient.invalidateQueries({ queryKey: ["leads", workspaceId] });
    },
  });

  return (
    <main className="min-h-screen bg-[#F8F7FC] p-4 sm:p-6 text-slate-950">
      <div className="mx-auto grid max-w-7xl gap-6">
        <header className="flex flex-col gap-4 rounded-2xl bg-white p-6 shadow-sm md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Sellora CRM</p>
            <h1 className="mt-2 text-3xl font-bold">Leads</h1>
            <p className="mt-1 text-slate-600">Capture, qualify, assign, and convert leads into customers.</p>
          </div>
          <button className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700" onClick={() => setIsCreateOpen(true)}>Create lead</button>
        </header>

        <section className="grid gap-3 rounded-2xl bg-white p-4 shadow-sm md:grid-cols-5">
          <input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Search leads" value={search} onChange={(event) => setSearch(event.target.value)} />
          <select className="rounded-md border border-slate-300 px-3 py-2" value={status} onChange={(event) => setStatus(event.target.value as LeadStatus | "")}>
            {STATUSES.map((item) => <option key={item || "all"} value={item}>{item || "All statuses"}</option>)}
          </select>
          <select className="rounded-md border border-slate-300 px-3 py-2" value={leadSourceId} onChange={(event) => setLeadSourceId(event.target.value)}>
            <option value="">All sources</option>
            {(sourcesQuery.data ?? []).map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}
          </select>
        </section>

        {leadsQuery.isError ? <p className="rounded-lg bg-rose-50 p-4 text-rose-700">Unable to load leads. Check workspace and authentication.</p> : null}
        <LeadTable leads={leadsQuery.data ?? []} leadSources={sourcesQuery.data ?? []} />

        {isCreateOpen ? (
          <div className="fixed inset-0 grid place-items-center bg-slate-950/40 p-4">
            <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-xl">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-xl font-bold">Create lead</h2>
                <button className="text-slate-500" onClick={() => setIsCreateOpen(false)}>Close</button>
              </div>
              <LeadForm leadSources={sourcesQuery.data ?? []} onSubmit={(values) => createMutation.mutate(values)} />
            </div>
          </div>
        ) : null}
      </div>
    </main>
  );
}
