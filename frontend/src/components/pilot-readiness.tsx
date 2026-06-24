"use client";

import Link from "next/link";
import { CheckCircle2, Circle, Sparkles } from "lucide-react";
import { useI18n } from "@/i18n/provider";

type WorkspaceLike = { workspace_slug?: string | null; workspace_name?: string | null } | null | undefined;
type SetupChecklistItem = { key: string; href: string; done: boolean };

export function isDemoWorkspace(workspace: WorkspaceLike) {
  const slug = workspace?.workspace_slug?.toLowerCase() ?? "";
  const name = workspace?.workspace_name?.toLowerCase() ?? "";
  return slug === "sellora-demo" || slug.includes("demo") || name.includes("demo");
}

export function DemoWorkspaceNotice({ workspace }: { workspace: WorkspaceLike }) {
  const { t } = useI18n();
  if (!isDemoWorkspace(workspace)) return null;
  return (
    <section className="min-w-0 overflow-hidden rounded-[24px] border border-violet-200 bg-violet-50 p-4 text-violet-950 shadow-sm dark:border-violet-400/30 dark:bg-violet-500/10 dark:text-violet-50">
      <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-xs font-black uppercase tracking-[0.18em] text-violet-700 shadow-sm dark:bg-white/10 dark:text-violet-100"><Sparkles className="h-4 w-4" />{t("demoWorkspace.badge")}</p>
          <h2 className="mt-3 text-lg font-black">{t("demoWorkspace.title")}</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-violet-800 dark:text-violet-100">{t("demoWorkspace.description")}</p>
        </div>
        <Link className="min-h-11 rounded-2xl bg-violet-700 px-4 py-3 text-center text-sm font-black text-white shadow-sm" href="/analytics">{t("demoWorkspace.cta")}</Link>
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
