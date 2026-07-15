"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { WorkspacePage, WorkspaceHeader } from "@/components/crm-workspace";
import { Card, FormField, Input, Select, Button, StatusBadge } from "@/components/ui/primitives";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { safeApiErrorMessage } from "@/services/api";
import { CurrencyCode, fetchWorkspaceSettings, updateWorkspaceSettings } from "@/services/workspaces";

const timezones = ["Europe/Kyiv", "UTC"];

export default function WorkspaceSettingsPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { currentWorkspaceId, currentWorkspace, reloadCurrentUser } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const canManage = currentWorkspace?.role === "OWNER";
  const [form, setForm] = useState({ name: "", slug: "", currency_code: "UAH" as CurrencyCode, timezone: "Europe/Kyiv" });
  const [baseline, setBaseline] = useState(form);
  const [message, setMessage] = useState<{ tone: "success" | "danger"; text: string } | null>(null);
  const settings = useQuery({ queryKey: ["workspace-settings", workspaceId], queryFn: () => fetchWorkspaceSettings(workspaceId), enabled: Boolean(workspaceId) });
  const dirty = useMemo(() => JSON.stringify(form) !== JSON.stringify(baseline), [form, baseline]);
  const slugValid = /^[a-z0-9]+(-[a-z0-9]+)*$/.test(form.slug);
  const save = useMutation({
    mutationFn: () => updateWorkspaceSettings(workspaceId, form),
    onSuccess: async (updated) => {
      const next = { name: updated.name, slug: updated.slug, currency_code: updated.currency_code, timezone: updated.timezone };
      setForm(next); setBaseline(next); setMessage({ tone: "success", text: t("settings.workspacePage.saved") });
      await queryClient.invalidateQueries({ queryKey: ["workspace-settings", workspaceId] });
      await reloadCurrentUser();
    },
    onError: (error) => setMessage({ tone: "danger", text: safeApiErrorMessage(error, t("settings.workspacePage.saveFailed")) }),
  });
  useEffect(() => { if (settings.data) { const next = { name: settings.data.name, slug: settings.data.slug, currency_code: settings.data.currency_code, timezone: settings.data.timezone }; setForm(next); setBaseline(next); setMessage(null); } }, [settings.data, workspaceId]);
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (!canManage || !dirty || !slugValid) return; setMessage(null); save.mutate(); }

  return <WorkspacePage>
    <WorkspaceHeader eyebrow={t("settings.label")} title={t("settings.workspacePage.title")} description={t("settings.workspacePage.description")} actions={!canManage ? <StatusBadge tone="warning">{t("settings.ownerOnly")}</StatusBadge> : null} />
    <section className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,760px)_minmax(280px,1fr)]">
      <Card>
        <form className="grid gap-5" onSubmit={submit}>
          {settings.isLoading ? <p className="rounded-2xl border border-border-subtle bg-surface-2 p-3 text-sm font-bold text-text-secondary">{t("settings.workspacePage.loading")}</p> : null}
          {settings.isError ? <p className="rounded-2xl border border-danger/25 bg-[var(--danger-surface)] p-3 text-sm font-bold text-[var(--danger-foreground)]">{t("settings.workspacePage.loadFailed")}</p> : null}
          <FormField label={t("settings.workspacePage.nameLabel")} hint={t("settings.workspacePage.nameHint")}><Input value={form.name} onChange={(e) => { setForm({ ...form, name: e.target.value }); setMessage(null); }} disabled={!canManage || save.isPending} required /></FormField>
          <FormField label={t("settings.workspacePage.slugLabel")} hint={t("settings.workspacePage.slugHint")} error={form.slug && !slugValid ? t("settings.workspacePage.slugError") : null}><Input value={form.slug} onChange={(e) => { setForm({ ...form, slug: e.target.value.toLowerCase() }); setMessage(null); }} disabled={!canManage || save.isPending} required aria-invalid={form.slug && !slugValid ? true : undefined} /></FormField>
          <div className="grid gap-4 sm:grid-cols-2"><FormField label={t("settings.currency")} hint={t("settings.currencyHelp")}><Select value={form.currency_code} onChange={(e) => { setForm({ ...form, currency_code: e.target.value as CurrencyCode }); setMessage(null); }} disabled={!canManage || save.isPending}><option value="UAH">{t("settings.currencyLabels.UAH")}</option><option value="USD">{t("settings.currencyLabels.USD")}</option></Select></FormField><FormField label={t("settings.workspacePage.timezoneLabel")} hint={t("settings.workspacePage.timezoneHint")}><Select value={form.timezone} onChange={(e) => { setForm({ ...form, timezone: e.target.value }); setMessage(null); }} disabled={!canManage || save.isPending}>{timezones.map((tz) => <option key={tz} value={tz}>{tz}</option>)}</Select></FormField></div>
          {message ? <p className={`inline-flex items-center gap-2 rounded-2xl border p-3 text-sm font-bold ${message.tone === "success" ? "border-success/25 bg-[var(--success-surface)] text-[var(--success-foreground)]" : "border-danger/25 bg-[var(--danger-surface)] text-[var(--danger-foreground)]"}`}>{message.tone === "success" ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}{message.text}</p> : null}
          <div className="flex flex-col-reverse gap-3 border-t border-border-subtle pt-4 sm:flex-row sm:justify-end"><Button type="button" variant="secondary" disabled={!dirty || save.isPending} onClick={() => { setForm(baseline); setMessage(null); }}>{t("actions.cancel")}</Button><Button type="submit" loading={save.isPending} disabled={!canManage || !dirty || !slugValid}>{t("actions.saveChanges")}</Button></div>
        </form>
      </Card>
      <Card className="self-start"><p className="text-xs font-black uppercase tracking-[0.16em] text-text-muted">{t("settings.workspacePage.safetyTitle")}</p><h2 className="mt-2 text-xl font-black text-text-primary">{t("settings.workspacePage.safetyHeading")}</h2><p className="mt-2 text-sm leading-6 text-text-secondary">{t("settings.workspacePage.safetyDescription")}</p><div className="mt-4 rounded-3xl border border-warning/25 bg-[var(--warning-surface)] p-4 text-sm leading-6 text-[var(--warning-foreground)]">{t("settings.workspacePage.dangerUnavailable")}</div></Card>
    </section>
  </WorkspacePage>;
}
