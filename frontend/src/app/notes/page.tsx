"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, Check, CheckCircle2, ClipboardList, FileText, Pencil, Pin, Plus, Search, Trash2 } from "lucide-react";

import { WorkspaceHeader, WorkspacePage } from "@/components/crm-workspace";
import { MemoEditor } from "@/components/memo-editor";
import { Button } from "@/components/ui/primitives";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { dateLabel, kyivDateKey } from "@/lib/planner-dates";
import { createWorkspaceMemo, deleteWorkspaceMemo, fetchWorkspaceMemos, updateWorkspaceMemo } from "@/services/workspace-memos";
import { WorkspaceMemo, WorkspaceMemoCreate } from "@/types/workspace-memo";

type Filter = "ALL" | "NOTE" | "TASK" | "OPEN";

export default function NotesPage() {
  const { t, locale } = useI18n();
  const { currentWorkspaceId, currentWorkspace, status } = useAuth();
  const queryClient = useQueryClient();
  const workspaceId = currentWorkspaceId ?? "";
  const enabled = status === "authenticated" && Boolean(workspaceId);
  const canEdit = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";
  const [editorKind, setEditorKind] = useState<"NOTE" | "TASK" | null>(null);
  const [editing, setEditing] = useState<WorkspaceMemo | null>(null);
  const [queryText, setQueryText] = useState("");
  const [filter, setFilter] = useState<Filter>("ALL");
  const today = kyivDateKey();
  useEffect(() => { setEditorKind(null); setEditing(null); setQueryText(""); }, [workspaceId]);
  const memos = useQuery({
    queryKey: ["workspace-memos", workspaceId],
    queryFn: () => fetchWorkspaceMemos(workspaceId), enabled,
  });
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["workspace-memos", workspaceId] });
  const save = useMutation({
    mutationFn: async (payload: WorkspaceMemoCreate) => editing
      ? updateWorkspaceMemo(workspaceId, editing.id, { title: payload.title, body: payload.body, due_on: payload.due_on, is_pinned: payload.is_pinned })
      : createWorkspaceMemo(workspaceId, payload),
    onSuccess: () => { setEditing(null); setEditorKind(null); void invalidate(); },
  });
  const update = useMutation({
    mutationFn: ({ id, changes }: { id: string; changes: { is_done?: boolean; is_pinned?: boolean } }) => updateWorkspaceMemo(workspaceId, id, changes),
    onSuccess: () => { void invalidate(); },
  });
  const remove = useMutation({
    mutationFn: (id: string) => deleteWorkspaceMemo(workspaceId, id),
    onSuccess: () => { void invalidate(); },
  });

  const records = memos.data ?? [];
  const pending = records.filter((item) => item.kind === "TASK" && !item.is_done).length;
  const overdue = records.filter((item) => item.kind === "TASK" && !item.is_done && item.due_on && item.due_on < today).length;
  const pinned = records.filter((item) => item.is_pinned).length;
  const rows = useMemo(() => records.filter((item) => {
    const matchesKind = filter === "ALL" || (filter === "OPEN" ? item.kind === "TASK" && !item.is_done : item.kind === filter);
    return matchesKind && (item.title + " " + item.body).toLocaleLowerCase(locale).includes(queryText.trim().toLocaleLowerCase(locale));
  }).sort((a, b) => Number(b.is_pinned) - Number(a.is_pinned) || Number(a.is_done) - Number(b.is_done) || b.created_at.localeCompare(a.created_at)), [records, filter, queryText, locale]);
  const filterKeys: Filter[] = ["ALL", "NOTE", "TASK", "OPEN"];

  return <WorkspacePage>
    <WorkspaceHeader title={t("navigation.notes")} description={t("planner.notesSubtitle")} actions={canEdit ? (
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => { save.reset(); setEditing(null); setEditorKind("TASK"); }}><ClipboardList className="h-4 w-4" />{t("planner.newTask")}</Button>
        <Button onClick={() => { save.reset(); setEditing(null); setEditorKind("NOTE"); }}><Plus className="h-4 w-4" />{t("planner.newNote")}</Button>
      </div>
    ) : undefined} />

    <div className="grid grid-cols-3 gap-2 sm:gap-3" aria-label={t("planner.summary")}>
      {[
        { label: t("planner.allCount"), count: records.length, icon: FileText },
        { label: t("planner.openCount"), count: pending, icon: ClipboardList },
        { label: t("planner.overdueCount"), count: overdue, icon: CalendarDays },
      ].map(({ label, count, icon: Icon }) => <div key={label} className="min-w-0 rounded-2xl border border-border-subtle bg-surface-1 p-3 sm:p-4">
        <div className="flex items-center gap-2 text-xs text-text-muted"><Icon className="hidden h-4 w-4 shrink-0 sm:block" /> <span className="min-w-0 truncate">{label}</span></div>
        <p className="mt-2 text-2xl font-semibold tabular-nums text-text-primary">{memos.isLoading ? "—" : count}</p>
      </div>)}
    </div>

    {canEdit && editorKind ? <MemoEditor key={editing?.id ?? editorKind} kind={editorKind} initial={editing} saving={save.isPending} error={save.isError ? t("planner.saveError") : null} onSave={(payload) => save.mutate(payload)} onCancel={() => { setEditorKind(null); setEditing(null); }} /> : null}

    <section className="grid min-w-0 gap-3">
      <div className="flex flex-col gap-3 rounded-2xl border border-border-subtle bg-surface-1 p-3 sm:flex-row sm:items-center">
        <label className="flex min-h-11 min-w-0 flex-1 items-center gap-2 rounded-xl border border-border-subtle bg-surface-2 px-3">
          <Search className="h-4 w-4 shrink-0 text-text-muted" />
          <input className="w-full min-w-0 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-muted" placeholder={t("planner.search")} aria-label={t("planner.search")} value={queryText} onChange={(e) => setQueryText(e.target.value)} />
        </label>
        <div className="flex min-w-0 gap-1 overflow-x-auto" role="group" aria-label={t("planner.filterLabel")}>
          {filterKeys.map(key => <button key={key} type="button" onClick={() => setFilter(key)} aria-pressed={filter === key} className={`min-h-10 shrink-0 rounded-xl px-3 text-xs font-semibold transition ${filter === key ? "bg-primary/15 text-primary" : "text-text-secondary hover:bg-surface-hover"}`}>{t(`planner.filter.${key}`)}</button>)}
        </div>
      </div>
      {memos.isLoading ? <LoadingSkeleton rows={3} /> : null}
      {memos.isError ? <ErrorState description={t("planner.loadError")} onRetry={() => void memos.refetch()} /> : null}
      {remove.isError || update.isError ? <p role="alert" className="rounded-xl bg-[var(--danger-surface)] px-3 py-2 text-sm text-danger">{t("planner.saveError")}</p> : null}
      {!memos.isLoading && !memos.isError && rows.length === 0 ? (
        <EmptyState title={records.length ? t("planner.noMatches") : t("planner.emptyTitle")} description={records.length ? t("planner.noMatchesHint") : t("planner.emptyHint")}
          action={canEdit && records.length === 0 ? <Button onClick={() => setEditorKind("NOTE")}><Plus className="h-4 w-4" />{t("planner.newNote")}</Button> : null} />
      ) : null}
      {!memos.isLoading && !memos.isError && rows.length > 0 ? <div className="grid min-w-0 gap-3 md:grid-cols-2 2xl:grid-cols-3" data-workspace-note-grid>
        {rows.map(item => <article key={item.id} className="group flex min-w-0 flex-col gap-3 rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-[var(--shadow-card)]">
          <div className="flex min-w-0 items-start gap-3">
            {item.kind === "TASK" ? <button type="button" disabled={!canEdit || update.isPending} onClick={() => update.mutate({ id: item.id, changes: { is_done: !item.is_done } })} aria-label={item.is_done ? t("planner.reopen") : t("planner.complete")} className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl border transition ${item.is_done ? "border-success/30 bg-[var(--success-surface)] text-success" : "border-border-subtle bg-surface-2 text-text-muted hover:border-primary"}`}>{item.is_done ? <CheckCircle2 className="h-5 w-5" /> : <Check className="h-5 w-5" />}</button> : <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary"><FileText className="h-5 w-5" /></span>}
            <div className="min-w-0 flex-1"><div className="flex items-center gap-2">{item.is_pinned ? <Pin className="h-3.5 w-3.5 shrink-0 text-primary" aria-label={t("planner.pin")} /> : null}<h2 className={`min-w-0 break-words text-sm font-semibold text-text-primary ${item.is_done ? "line-through opacity-60" : ""}`}>{item.title}</h2></div>
              <p className="mt-1 text-xs text-text-muted">{item.kind === "TASK" ? t("planner.task") : t("planner.note")}{item.due_on ? ` · ${dateLabel(item.due_on, locale)}` : ""}</p>
            </div>
          </div>
          {item.body ? <p className="line-clamp-4 whitespace-pre-wrap break-words text-sm leading-6 text-text-secondary">{item.body}</p> : null}
          <div className="mt-auto flex items-center justify-between gap-2 border-t border-border-subtle pt-2">
            <span className="text-xs text-text-muted">{item.kind === "TASK" && !item.is_done && item.due_on && item.due_on < today ? t("planner.overdue") : item.kind === "TASK" && item.is_done ? t("planner.done") : t("planner.saved")}</span>
            {canEdit ? <div className="flex gap-1">
              <button type="button" className="grid h-10 w-10 place-items-center rounded-xl text-text-secondary hover:bg-surface-hover" title={item.is_pinned ? t("planner.unpin") : t("planner.pin")} aria-label={item.is_pinned ? t("planner.unpin") : t("planner.pin")} onClick={() => update.mutate({ id: item.id, changes: { is_pinned: !item.is_pinned } })}><Pin className="h-4 w-4" /></button>
              <button type="button" className="grid h-10 w-10 place-items-center rounded-xl text-text-secondary hover:bg-surface-hover" title={t("planner.edit")} aria-label={t("planner.edit")} onClick={() => { save.reset(); setEditing(item); setEditorKind(item.kind); window.scrollTo({ top: 0, behavior: "smooth" }); }}><Pencil className="h-4 w-4" /></button>
              <button type="button" disabled={remove.isPending} className="grid h-10 w-10 place-items-center rounded-xl text-text-muted hover:bg-[var(--danger-surface)] hover:text-danger" title={t("planner.delete")} aria-label={t("planner.delete")} onClick={() => { if (window.confirm(t("planner.deleteConfirm"))) remove.mutate(item.id); }}><Trash2 className="h-4 w-4" /></button>
            </div> : null}
          </div>
        </article>)}
      </div> : null}
    </section>
    {pinned > 0 ? <p className="text-xs text-text-muted">{t("planner.pinnedCount", { count: pinned })}</p> : null}
    <Link href="/calendar" className="inline-flex w-fit min-h-11 items-center gap-2 text-sm font-semibold text-primary hover:underline"><CalendarDays className="h-4 w-4" />{t("planner.openCalendar")}</Link>
  </WorkspacePage>;
}
