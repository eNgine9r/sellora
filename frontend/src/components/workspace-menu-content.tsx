"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { safeApiErrorMessage } from "@/services/api";
import { createWorkspace } from "@/services/workspaces";
import { authStorage } from "@/services/auth.service";
import { WorkspaceMembership } from "@/types/auth";

type Labels = {
  workspace: string;
  currentWorkspace: string;
  switchWorkspace: string;
  createWorkspace: string;
  storeName: string;
  slug: string;
  creating: string;
  emptyWorkspace: string;
  createError: string;
};

export function WorkspaceMenuContent({ memberships, currentWorkspaceId, labels, onSwitchWorkspace, onCreated, onClose }: { memberships: WorkspaceMembership[]; currentWorkspaceId: string | null; labels: Labels; onSwitchWorkspace: (workspaceId: string) => void; onCreated: () => Promise<void>; onClose?: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [error, setError] = useState<string | null>(null);
  const activeWorkspace = memberships.find((item) => item.workspace_id === currentWorkspaceId);
  const createMutation = useMutation({
    mutationFn: () => createWorkspace({ name, slug, currency_code: "UAH", timezone: "Europe/Kyiv" }),
    onSuccess: async (workspace) => {
      authStorage.setCurrentWorkspaceId(workspace.id);
      setName("");
      setSlug("");
      setError(null);
      await queryClient.invalidateQueries();
      await onCreated();
      onClose?.();
    },
    onError: (err) => setError(safeApiErrorMessage(err, labels.createError)),
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    createMutation.mutate();
  }

  return (
    <section className="grid min-w-0 gap-3" aria-label={labels.workspace}>
      <div className="rounded-3xl border border-violet-100 bg-violet-50/80 p-3 dark:border-violet-400/20 dark:bg-violet-400/10">
        <p className="text-xs font-black uppercase tracking-[0.18em] text-violet-700 dark:text-violet-200">{labels.currentWorkspace}</p>
        <p className="mt-1 truncate text-base font-black text-slate-950 dark:text-white">{activeWorkspace?.workspace_name ?? labels.workspace}</p>
      </div>
      <div className="grid gap-1">
        <p className="px-1 text-xs font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">{labels.switchWorkspace}</p>
        {memberships.length ? memberships.map((membership) => (
          <button
            key={membership.workspace_id}
            type="button"
            className={`min-h-11 rounded-2xl px-3 py-2 text-left text-sm font-bold transition ${membership.workspace_id === currentWorkspaceId ? "bg-violet-600 text-white shadow-lg shadow-violet-500/20" : "bg-white text-slate-800 hover:bg-slate-50 dark:bg-white/5 dark:text-slate-100 dark:hover:bg-white/10"}`}
            onClick={() => {
              onSwitchWorkspace(membership.workspace_id);
              onClose?.();
            }}
          >
            <span className="block truncate">{membership.workspace_name}</span>
            <span className={`text-xs ${membership.workspace_id === currentWorkspaceId ? "text-violet-100" : "text-slate-500 dark:text-slate-400"}`}>{membership.role}</span>
          </button>
        )) : <p className="rounded-2xl bg-slate-50 p-3 text-sm text-slate-600 dark:bg-white/5 dark:text-slate-300">{labels.emptyWorkspace}</p>}
      </div>
      <form className="grid gap-2 rounded-3xl border border-slate-100 p-3 dark:border-white/10" onSubmit={submit}>
        <p className="text-sm font-black text-slate-950 dark:text-white">+ {labels.createWorkspace}</p>
        <input className="min-h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-950 outline-none focus:border-violet-300 focus:ring-4 focus:ring-violet-100 dark:border-white/10 dark:bg-white/10 dark:text-white" placeholder={labels.storeName} value={name} onChange={(event) => setName(event.target.value)} required />
        <input className="min-h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-950 outline-none focus:border-violet-300 focus:ring-4 focus:ring-violet-100 dark:border-white/10 dark:bg-white/10 dark:text-white" placeholder={labels.slug} value={slug} onChange={(event) => setSlug(event.target.value)} required pattern="[a-z0-9]+(-[a-z0-9]+)*" />
        {error ? <p className="rounded-xl bg-red-50 px-3 py-2 text-xs font-bold text-red-700 dark:bg-red-500/10 dark:text-red-200">{error}</p> : null}
        <button className="min-h-10 rounded-xl bg-violet-600 px-3 text-sm font-black text-white transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={createMutation.isPending} type="submit">
          {createMutation.isPending ? labels.creating : `+ ${labels.createWorkspace}`}
        </button>
      </form>
    </section>
  );
}
