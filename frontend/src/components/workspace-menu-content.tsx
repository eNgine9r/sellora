"use client";

import { FormEvent, useState } from "react";
import { Check, ChevronDown, Plus, Store, X } from "lucide-react";
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
  roleOwner: string;
  roleManager: string;
  roleAnalyst: string;
  cancel: string;
};

export function WorkspaceMenuContent({ memberships, currentWorkspaceId, labels, onSwitchWorkspace, onCreated, onClose }: { memberships: WorkspaceMembership[]; currentWorkspaceId: string | null; labels: Labels; onSwitchWorkspace: (workspaceId: string) => void; onCreated: () => Promise<void>; onClose?: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showWorkspaces, setShowWorkspaces] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const activeWorkspace = memberships.find((item) => item.workspace_id === currentWorkspaceId);
  const otherWorkspaces = memberships.filter((item) => item.workspace_id !== currentWorkspaceId);
  const roleLabel = (role: WorkspaceMembership["role"]) => ({
    OWNER: labels.roleOwner,
    MANAGER: labels.roleManager,
    ANALYST: labels.roleAnalyst,
  })[role];

  const createMutation = useMutation({
    mutationFn: () => createWorkspace({ name: name.trim(), slug: slug.trim(), currency_code: "UAH", timezone: "Europe/Kyiv" }),
    onSuccess: async (workspace) => {
      authStorage.setCurrentWorkspaceId(workspace.id);
      setName("");
      setSlug("");
      setError(null);
      setShowCreate(false);
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
    <section className="grid min-w-0 gap-2" aria-label={labels.workspace}>
      <p className="px-1 text-xs font-semibold text-text-muted">{labels.workspace}</p>
      <div className="rounded-2xl border border-border-subtle bg-surface-2 px-3 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary"><Store className="h-5 w-5" aria-hidden="true" /></span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-text-primary">{activeWorkspace?.workspace_name ?? labels.workspace}</p>
            {activeWorkspace ? <p className="text-xs text-text-muted">{roleLabel(activeWorkspace.role)}</p> : null}
          </div>
          {otherWorkspaces.length > 0 ? (
            <button type="button" aria-label={labels.switchWorkspace} aria-expanded={showWorkspaces} onClick={() => { setShowWorkspaces((value) => !value); setShowCreate(false); }} className="grid h-11 w-11 shrink-0 place-items-center rounded-xl text-text-secondary transition hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring">
              <ChevronDown className={`h-4 w-4 transition-transform ${showWorkspaces ? "rotate-180" : ""}`} aria-hidden="true" />
            </button>
          ) : null}
        </div>
      </div>

      {showWorkspaces ? (
        <div className="grid gap-1 rounded-2xl border border-border-subtle bg-surface-1 p-1" aria-label={labels.switchWorkspace}>
          {otherWorkspaces.map((membership) => (
            <button key={membership.workspace_id} type="button" className="flex min-h-11 items-center gap-2 rounded-xl px-3 py-2 text-left transition hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" onClick={() => { onSwitchWorkspace(membership.workspace_id); onClose?.(); }}>
              <span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium text-text-primary">{membership.workspace_name}</span><span className="block text-xs text-text-muted">{roleLabel(membership.role)}</span></span>
            </button>
          ))}
        </div>
      ) : null}
      {!memberships.length ? <p className="px-2 text-xs text-text-muted">{labels.emptyWorkspace}</p> : null}

      {!showCreate ? (
        <button type="button" onClick={() => { setShowCreate(true); setShowWorkspaces(false); }} className="flex min-h-11 items-center gap-2 rounded-xl px-3 text-left text-sm font-medium text-text-secondary transition hover:bg-surface-hover hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring">
          <Plus className="h-4 w-4" aria-hidden="true" /> {labels.createWorkspace}
        </button>
      ) : (
        <form className="grid gap-3 rounded-2xl border border-border-subtle bg-surface-2 p-3" onSubmit={submit}>
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-semibold text-text-primary">{labels.createWorkspace}</p>
            <button type="button" onClick={() => { setShowCreate(false); setError(null); }} aria-label={labels.cancel} className="grid h-11 w-11 place-items-center rounded-xl text-text-muted hover:bg-surface-hover"><X className="h-4 w-4" aria-hidden="true" /></button>
          </div>
          <label className="grid gap-1 text-xs font-medium text-text-secondary">{labels.storeName}
            <input className="min-h-11 min-w-0 rounded-xl border border-border-subtle bg-surface-3 px-3 text-sm text-text-primary outline-none focus:ring-2 focus:ring-focus-ring" value={name} onChange={(event) => setName(event.target.value)} required maxLength={255} autoComplete="off" />
          </label>
          <label className="grid gap-1 text-xs font-medium text-text-secondary">{labels.slug}
            <input className="min-h-11 min-w-0 rounded-xl border border-border-subtle bg-surface-3 px-3 text-sm text-text-primary outline-none focus:ring-2 focus:ring-focus-ring" value={slug} onChange={(event) => setSlug(event.target.value.toLowerCase())} required pattern="[a-z0-9]+(-[a-z0-9]+)*" autoComplete="off" />
          </label>
          {error ? <p role="alert" className="text-xs text-danger">{error}</p> : null}
          <button type="submit" disabled={createMutation.isPending} className="flex min-h-11 items-center justify-center gap-2 rounded-xl bg-primary px-3 text-sm font-semibold text-primary-foreground transition hover:bg-primary-hover disabled:opacity-60">
            <Check className="h-4 w-4" aria-hidden="true" /> {createMutation.isPending ? labels.creating : labels.createWorkspace}
          </button>
        </form>
      )}
    </section>
  );
}
