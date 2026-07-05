"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { safeApiErrorMessage } from "@/services/api";
import { createWorkspace } from "@/services/workspaces";
import { authStorage } from "@/services/auth.service";
import { WorkspaceMembership } from "@/types/auth";

export function WorkspaceSwitcher({ memberships, currentWorkspaceId, onSwitchWorkspace, onCreated }: { memberships: WorkspaceMembership[]; currentWorkspaceId: string | null; onSwitchWorkspace: (workspaceId: string) => void; onCreated: () => Promise<void> }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [error, setError] = useState<string | null>(null);
  const createMutation = useMutation({
    mutationFn: () => createWorkspace({ name, slug, currency_code: "UAH", timezone: "Europe/Kyiv" }),
    onSuccess: async (workspace) => {
      authStorage.setCurrentWorkspaceId(workspace.id);
      onSwitchWorkspace(workspace.id);
      setName("");
      setSlug("");
      setError(null);
      setOpen(false);
      await queryClient.invalidateQueries();
      await onCreated();
    },
    onError: (err) => setError(safeApiErrorMessage(err, "Не вдалося створити робочий простір.")),
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    createMutation.mutate();
  }

  const activeName = memberships.find((item) => item.workspace_id === currentWorkspaceId)?.workspace_name ?? "Робочий простір";
  return (
    <div className="relative min-w-0">
      <button type="button" className="min-h-11 max-w-[240px] truncate rounded-2xl border border-slate-200 bg-white px-3 text-left text-sm font-black text-slate-800 shadow-sm dark:border-white/10 dark:bg-white/10 dark:text-white" onClick={() => setOpen((value) => !value)} aria-label="Перемкнути робочий простір">
        {activeName} <span className="text-slate-400">▾</span>
      </button>
      {open ? (
        <div className="absolute right-0 z-50 mt-2 w-[min(92vw,360px)] rounded-3xl border border-slate-200 bg-white p-3 shadow-2xl dark:border-white/10 dark:bg-slate-950">
          <p className="px-2 text-xs font-black uppercase tracking-[0.18em] text-violet-600">Робочий простір</p>
          <div className="mt-2 grid gap-1">
            {memberships.length ? memberships.map((membership) => (
              <button key={membership.workspace_id} type="button" className={`rounded-2xl px-3 py-2 text-left text-sm font-bold ${membership.workspace_id === currentWorkspaceId ? "bg-violet-50 text-violet-700" : "hover:bg-slate-50 dark:hover:bg-white/10"}`} onClick={() => { onSwitchWorkspace(membership.workspace_id); setOpen(false); }}>
                {membership.workspace_name}<span className="ml-2 text-xs text-slate-500">{membership.role}</span>
              </button>
            )) : <p className="rounded-2xl bg-slate-50 p-3 text-sm text-slate-600">У вас ще немає робочого простору. Створіть перший магазин, щоб почати роботу в Sellora.</p>}
          </div>
          <form className="mt-3 grid gap-2 border-t border-slate-100 pt-3" onSubmit={submit}>
            <p className="text-sm font-black text-slate-900 dark:text-white">+ Створити робочий простір</p>
            <input className="min-h-10 rounded-xl border border-slate-200 px-3 text-sm dark:border-white/10 dark:bg-white/10" placeholder="Назва магазину" value={name} onChange={(event) => setName(event.target.value)} required />
            <input className="min-h-10 rounded-xl border border-slate-200 px-3 text-sm dark:border-white/10 dark:bg-white/10" placeholder="Slug / коротка назва" value={slug} onChange={(event) => setSlug(event.target.value)} required pattern="[a-z0-9]+(-[a-z0-9]+)*" />
            {error ? <p className="rounded-xl bg-red-50 px-3 py-2 text-xs font-bold text-red-700">{error}</p> : null}
            <button className="min-h-10 rounded-xl bg-violet-600 px-3 text-sm font-black text-white disabled:opacity-60" disabled={createMutation.isPending}>{createMutation.isPending ? "Створення…" : "+ Створити робочий простір"}</button>
          </form>
        </div>
      ) : null}
    </div>
  );
}
