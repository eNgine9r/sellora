"use client";

import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Circle, Sparkles, Trash2 } from "lucide-react";
import { useI18n } from "@/i18n/provider";
import { useAuth } from "@/hooks/use-auth";
import { authStorage } from "@/services/auth.service";
import { createDemoWorkspace, deactivateDemoWorkspace } from "@/services/workspaces";
import { OnboardingStatus } from "@/services/onboarding";

type SetupChecklistItem = { key: string; href: string; done: boolean };

export function FirstRunChecklist({ status }: { status: OnboardingStatus | undefined }) {
  const { t } = useI18n();
  const role = status?.role ?? "OWNER";
  const ownerItems = [
    { key: "workspace", href: "/settings/workspace", done: Boolean(status?.steps.workspace_configured), allowed: role === "OWNER" },
    { key: "product", href: "/products", done: Boolean(status?.steps.product_created), allowed: role !== "ANALYST" },
    { key: "stock", href: "/inventory", done: Boolean(status?.steps.stock_added), allowed: role !== "ANALYST" },
    { key: "lead", href: "/leads", done: Boolean(status?.steps.lead_or_customer_created), allowed: role !== "ANALYST" },
    { key: "order", href: "/orders", done: Boolean(status?.steps.order_created), allowed: role !== "ANALYST" },
  ];
  const analystItems = ["dashboard", "analytics", "finance", "advertising", "inventory"].map((key) => ({ key, href: key === "dashboard" ? "/dashboard" : `/${key}`, done: false, allowed: true }));
  const items = role === "ANALYST" ? analystItems : ownerItems;
  const completed = status?.completed_steps ?? items.filter((item) => item.done).length;
  const total = status?.total_steps ?? items.length;
  return (
    <section className="min-w-0 overflow-hidden rounded-[24px] border border-emerald-100 bg-white p-5 shadow-sm dark:border-emerald-400/20 dark:bg-slate-900" data-first-run-checklist>
      <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-600 dark:text-emerald-300">{t("gettingStarted.eyebrow")}</p>
          <h2 className="mt-2 text-xl font-black text-slate-950 dark:text-white">{t("gettingStarted.title")}</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-300">{role === "ANALYST" ? t("gettingStarted.analystDescription") : t("gettingStarted.description")}</p>
        </div>
        <span role="status" aria-label={t("gettingStarted.progress", { completed, total })} className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-black text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-200">{status?.progress_percent ?? 0}%</span>
      </div>
      <div className="mt-4 grid min-w-0 gap-3 md:grid-cols-2 xl:grid-cols-5">
        {items.map((item) => {
          const content = <><span className="flex items-start gap-2">{item.done ? <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" /> : <Circle className="mt-0.5 h-5 w-5 shrink-0 text-slate-400" />}<span><span className="block text-sm font-black text-slate-950 dark:text-white">{t(`gettingStarted.steps.${item.key}.title`)}</span><span className="mt-1 block text-xs leading-5 text-slate-500 dark:text-slate-300">{item.allowed ? t(`gettingStarted.steps.${item.key}.description`) : t("gettingStarted.restricted")}</span></span></span></>;
          return item.allowed ? <Link href={item.href} className="rounded-2xl border border-slate-100 bg-slate-50 p-4 hover:bg-emerald-50 dark:border-white/10 dark:bg-white/5" key={item.key}>{content}</Link> : <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4 opacity-80 dark:border-white/10 dark:bg-white/5" key={item.key}>{content}</div>;
        })}
      </div>
    </section>
  );
}

export function DemoWorkspaceActions({ workspaceId, isDemo }: { workspaceId?: string | null; isDemo?: boolean }) {
  const { t } = useI18n();
  const { reloadCurrentUser, switchWorkspace } = useAuth();
  const queryClient = useQueryClient();
  const createInFlight = useRef(false);
  const createMutation = useMutation({
    mutationFn: createDemoWorkspace,
    onSuccess: async (workspace) => {
      authStorage.setCurrentWorkspaceId(workspace.id);
      queryClient.clear();
      await reloadCurrentUser();
      switchWorkspace(workspace.id);
    },
  });
  const deactivateMutation = useMutation({
    mutationFn: () => deactivateDemoWorkspace(workspaceId ?? ""),
    onSuccess: async () => {
      authStorage.setCurrentWorkspaceId(null);
      queryClient.clear();
      await reloadCurrentUser();
    },
  });

  const createDemo = () => {
    if (createInFlight.current || createMutation.isPending) return;
    createInFlight.current = true;
    createMutation.mutate(undefined, {
      onSettled: () => {
        createInFlight.current = false;
      },
    });
  };

  if (isDemo) {
    return <button type="button" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl border border-violet-200 bg-white px-4 py-2 text-sm font-black text-violet-700 dark:border-violet-400/30 dark:bg-white/10 dark:text-violet-100" disabled={deactivateMutation.isPending || !workspaceId} onClick={() => window.confirm(t("demo.removeConfirm")) && deactivateMutation.mutate()}><Trash2 className="h-4 w-4" />{deactivateMutation.isPending ? t("demo.removing") : t("demo.remove")}</button>;
  }
  return <button type="button" className="inline-flex min-h-11 items-center justify-center rounded-2xl bg-violet-700 px-4 py-2 text-sm font-black text-white shadow-sm disabled:opacity-60" disabled={createMutation.isPending || createInFlight.current} onClick={createDemo}>{createMutation.isPending ? t("demo.creating") : t("demo.viewDemo")}</button>;
}


export function FirstRunChecklist({ status }: { status: OnboardingStatus | undefined }) {
  const { t } = useI18n();
  const role = status?.role ?? "OWNER";
  const ownerItems = [
    { key: "workspace", href: "/settings/workspace", done: Boolean(status?.steps.workspace_configured), allowed: role === "OWNER" },
    { key: "product", href: "/products", done: Boolean(status?.steps.product_created), allowed: role !== "ANALYST" },
    { key: "stock", href: "/inventory", done: Boolean(status?.steps.stock_added), allowed: role !== "ANALYST" },
    { key: "lead", href: "/leads", done: Boolean(status?.steps.lead_or_customer_created), allowed: role !== "ANALYST" },
    { key: "order", href: "/orders", done: Boolean(status?.steps.order_created), allowed: role !== "ANALYST" },
  ];
  const analystItems = ["dashboard", "analytics", "finance", "advertising", "inventory"].map((key) => ({ key, href: key === "dashboard" ? "/dashboard" : `/${key}`, done: false, allowed: true }));
  const items = role === "ANALYST" ? analystItems : ownerItems;
  const completed = status?.completed_steps ?? items.filter((item) => item.done).length;
  const total = status?.total_steps ?? items.length;
  return (
    <section className="min-w-0 overflow-hidden rounded-[24px] border border-emerald-100 bg-white p-5 shadow-sm dark:border-emerald-400/20 dark:bg-slate-900" data-first-run-checklist>
      <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-600 dark:text-emerald-300">{t("gettingStarted.eyebrow")}</p>
          <h2 className="mt-2 text-xl font-black text-slate-950 dark:text-white">{t("gettingStarted.title")}</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-300">{role === "ANALYST" ? t("gettingStarted.analystDescription") : t("gettingStarted.description")}</p>
        </div>
        <span role="status" aria-label={t("gettingStarted.progress", { completed, total })} className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-black text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-200">{status?.progress_percent ?? 0}%</span>
      </div>
      <div className="mt-4 grid min-w-0 gap-3 md:grid-cols-2 xl:grid-cols-5">
        {items.map((item) => {
          const content = <><span className="flex items-start gap-2">{item.done ? <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" /> : <Circle className="mt-0.5 h-5 w-5 shrink-0 text-slate-400" />}<span><span className="block text-sm font-black text-slate-950 dark:text-white">{t(`gettingStarted.steps.${item.key}.title`)}</span><span className="mt-1 block text-xs leading-5 text-slate-500 dark:text-slate-300">{item.allowed ? t(`gettingStarted.steps.${item.key}.description`) : t("gettingStarted.restricted")}</span></span></span></>;
          return item.allowed ? <Link href={item.href} className="rounded-2xl border border-slate-100 bg-slate-50 p-4 hover:bg-emerald-50 dark:border-white/10 dark:bg-white/5" key={item.key}>{content}</Link> : <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4 opacity-80 dark:border-white/10 dark:bg-white/5" key={item.key}>{content}</div>;
        })}
      </div>
    </section>
  );
}

export function DemoWorkspaceActions({ workspaceId, isDemo }: { workspaceId?: string | null; isDemo?: boolean }) {
  const { t } = useI18n();
  const { reloadCurrentUser, switchWorkspace } = useAuth();
  const queryClient = useQueryClient();
  const createMutation = useMutation({
    mutationFn: createDemoWorkspace,
    onSuccess: async (workspace) => {
      authStorage.setCurrentWorkspaceId(workspace.id);
      await queryClient.invalidateQueries();
      await reloadCurrentUser();
      switchWorkspace(workspace.id);
    },
  });
  const deactivateMutation = useMutation({
    mutationFn: () => deactivateDemoWorkspace(workspaceId ?? ""),
    onSuccess: async () => {
      authStorage.setCurrentWorkspaceId(null);
      queryClient.clear();
      await reloadCurrentUser();
    },
  });
  if (isDemo) {
    return <button type="button" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl border border-violet-200 bg-white px-4 py-2 text-sm font-black text-violet-700 dark:border-violet-400/30 dark:bg-white/10 dark:text-violet-100" disabled={deactivateMutation.isPending || !workspaceId} onClick={() => window.confirm(t("demo.removeConfirm")) && deactivateMutation.mutate()}><Trash2 className="h-4 w-4" />{deactivateMutation.isPending ? t("demo.removing") : t("demo.remove")}</button>;
  }
  return <button type="button" className="inline-flex min-h-11 items-center justify-center rounded-2xl bg-violet-700 px-4 py-2 text-sm font-black text-white shadow-sm disabled:opacity-60" disabled={createMutation.isPending} onClick={() => createMutation.mutate()}>{createMutation.isPending ? t("demo.creating") : t("demo.viewDemo")}</button>;
}

export function DemoWorkspaceNotice({ workspace }: { workspace: WorkspaceLike }) {
  const { t } = useI18n();
  const { currentWorkspaceId } = useAuth();
  if (!isDemoWorkspace(workspace)) return null;
  return (
    <section className="min-w-0 overflow-hidden rounded-[24px] border border-violet-200 bg-violet-50 p-4 text-violet-950 shadow-sm dark:border-violet-400/30 dark:bg-violet-500/10 dark:text-violet-50" data-demo-workspace-banner>
      <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-xs font-black uppercase tracking-[0.18em] text-violet-700 shadow-sm dark:bg-white/10 dark:text-violet-100"><Sparkles className="h-4 w-4" />{t("demoWorkspace.badge")}</p>
          <h2 className="mt-3 text-lg font-black">{t("demoWorkspace.title")}</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-violet-800 dark:text-violet-100">{t("demoWorkspace.description")}</p>
        </div>
        <div className="flex flex-col gap-2 sm:items-end"><Link className="min-h-11 rounded-2xl bg-violet-700 px-4 py-3 text-center text-sm font-black text-white shadow-sm" href="/analytics">{t("demoWorkspace.cta")}</Link><DemoWorkspaceActions workspaceId={currentWorkspaceId} isDemo /></div>
      </div>
    </section>
  );
}

export function SetupChecklist({ items }: { items: SetupChecklistItem[] }) {
  const { t } = useI18n();
  const completed = items.filter((item) => item.done).length;
  return (
    <section className="min-w-0 overflow-hidden rounded-[24px] border border-slate-100 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-slate-900">
      <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-black uppercase tracking-[0.18em] text-violet-600 dark:text-violet-300">{t("onboarding.eyebrow")}</p>
          <h2 className="mt-2 text-xl font-black text-slate-950 dark:text-white">{t("onboarding.title")}</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-300">{t("onboarding.description")}</p>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-black text-slate-700 dark:bg-white/10 dark:text-slate-200">{t("setupChecklist.progress", { completed, total: items.length })}</span>
      </div>
      <div className="mt-4 grid min-w-0 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => (
          <Link className="flex min-w-0 items-start gap-3 rounded-2xl border border-slate-100 bg-slate-50 p-4 transition hover:border-violet-200 hover:bg-violet-50 dark:border-white/10 dark:bg-white/5 dark:hover:bg-violet-500/10" href={item.href} key={item.key}>
            {item.done ? <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" /> : <Circle className="mt-0.5 h-5 w-5 shrink-0 text-slate-400" />}
            <span className="min-w-0"><span className="block text-sm font-black text-slate-950 dark:text-white">{t(`setupChecklist.${item.key}.title`)}</span><span className="mt-1 block text-xs leading-5 text-slate-500 dark:text-slate-300">{t(`setupChecklist.${item.key}.description`)}</span></span>
          </Link>
        ))}
      </div>
    </section>
  );
}

export function FirstRunEmptyCtas() {
  const { t } = useI18n();
  const actions = [
    ["products", "/products"], ["import", "/settings/import"], ["orders", "/orders"], ["ads", "/advertising"], ["integrations", "/settings/integrations"], ["analytics", "/analytics"],
  ];
  return <div className="flex flex-wrap justify-center gap-2">{actions.map(([key, href]) => <Link className="min-h-10 rounded-xl bg-slate-900 px-3 py-2 text-sm font-black text-white dark:bg-white dark:text-slate-950" href={href} key={key}>{t(`firstRun.ctas.${key}`)}</Link>)}</div>;
}

export function ImportPilotHelp() {
  const { t } = useI18n();
  return (
    <section className="min-w-0 max-w-full overflow-hidden rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-950 shadow-sm dark:border-blue-400/30 dark:bg-blue-500/10 dark:text-blue-50">
      <p className="font-black">{t("importHelp.title")}</p>
      <div className="mt-3 grid min-w-0 gap-2 md:grid-cols-2">
        {["dryRun", "warnings", "errors", "duplicates", "nextAction"].map((key) => <p className="break-words leading-6" key={key}>{t(`importHelp.${key}`)}</p>)}
      </div>
    </section>
  );
}
