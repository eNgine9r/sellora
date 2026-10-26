"use client";

import { FormEvent, useEffect, useState } from "react";
import { CalendarClock, Pin, X } from "lucide-react";
import { Button } from "@/components/ui/primitives";
import { useI18n } from "@/i18n/provider";
import { WorkspaceMemo, WorkspaceMemoCreate } from "@/types/workspace-memo";

export function MemoEditor({
  initial, kind = "NOTE", initialDueOn = null, saving, error, onSave, onCancel,
}: {
  initial?: WorkspaceMemo | null;
  kind?: "NOTE" | "TASK";
  initialDueOn?: string | null;
  saving?: boolean;
  error?: string | null;
  onSave: (payload: WorkspaceMemoCreate) => void;
  onCancel: () => void;
}) {
  const { t } = useI18n();
  const currentKind = initial?.kind ?? kind;
  const [title, setTitle] = useState(initial?.title ?? "");
  const [body, setBody] = useState(initial?.body ?? "");
  const [dueOn, setDueOn] = useState(initial?.due_on ?? initialDueOn ?? "");
  const [pinned, setPinned] = useState(initial?.is_pinned ?? false);

  useEffect(() => {
    setTitle(initial?.title ?? "");
    setBody(initial?.body ?? "");
    setDueOn(initial?.due_on ?? initialDueOn ?? "");
    setPinned(initial?.is_pinned ?? false);
  }, [initial?.id, initial?.title, initial?.body, initial?.due_on, initial?.is_pinned, initialDueOn]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim() || saving) return;
    onSave({
      kind: currentKind,
      title: title.trim(),
      body: body.trim(),
      due_on: currentKind === "TASK" && dueOn ? dueOn : null,
      is_pinned: pinned,
    });
  }

  const inputClass = "w-full min-w-0 rounded-xl border border-border-subtle bg-surface-2 px-3 py-3 text-sm text-text-primary outline-none transition placeholder:text-text-muted focus:border-primary focus:ring-2 focus:ring-primary/20";

  return (
    <form onSubmit={submit} className="grid min-w-0 gap-4 rounded-3xl border border-primary/30 bg-surface-1 p-4 shadow-[var(--shadow-card)] sm:p-5" aria-label={initial ? t("planner.edit") : t("planner.new")}>
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-base font-semibold text-text-primary">{initial ? t("planner.edit") : currentKind === "TASK" ? t("planner.newTask") : t("planner.newNote")}</p>
          <p className="mt-0.5 text-xs text-text-muted">{currentKind === "TASK" ? t("planner.taskHint") : t("planner.noteHint")}</p>
        </div>
        <button type="button" aria-label={t("actions.close")} onClick={onCancel} className="grid h-11 w-11 shrink-0 place-items-center rounded-xl text-text-secondary hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"><X className="h-5 w-5" /></button>
      </div>
      <label className="grid gap-1.5 text-xs font-medium text-text-secondary">
        {t("planner.titleLabel")}
        <input autoFocus required maxLength={180} value={title} onChange={(event) => setTitle(event.target.value)} placeholder={t("planner.titlePlaceholder")} className={inputClass} />
      </label>
      <label className="grid gap-1.5 text-xs font-medium text-text-secondary">
        {t("planner.bodyLabel")}
        <textarea rows={3} maxLength={10000} value={body} onChange={(event) => setBody(event.target.value)} placeholder={t("planner.bodyPlaceholder")} className={inputClass} />
      </label>
      {currentKind === "TASK" ? (
        <label className="grid gap-1.5 text-xs font-medium text-text-secondary">
          <span className="inline-flex items-center gap-2"><CalendarClock className="h-4 w-4" />{t("planner.dueLabel")}</span>
          <input type="date" value={dueOn} onChange={(event) => setDueOn(event.target.value)} className={`sellora-date-input ${inputClass}`} />
        </label>
      ) : null}
      <label className="flex min-h-11 items-center gap-3 text-sm text-text-secondary">
        <input type="checkbox" className="h-4 w-4 accent-primary" checked={pinned} onChange={(event) => setPinned(event.target.checked)} />
        <Pin className="h-4 w-4" aria-hidden="true" />{t("planner.pin")}
      </label>
      {error ? <p role="alert" className="text-sm text-danger">{error}</p> : null}
      <div className="flex flex-wrap justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>{t("planner.cancel")}</Button>
        <Button type="submit" loading={saving} disabled={!title.trim()}>{t("planner.save")}</Button>
      </div>
    </form>
  );
}
