"use client";
import { useI18n } from "@/i18n/provider";

export type DashboardActivity = { label: string; date: string };
export function ActivityFeed({ events = [] }: { events?: DashboardActivity[] }) {
  const { t } = useI18n();
  return <section className="min-w-0 rounded-[20px] border border-slate-100 bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.06)] dark:border-white/10 dark:bg-slate-900 dark:shadow-none"><h2 className="text-lg font-black text-slate-950 dark:text-white">{t("dashboard.activity")}</h2><div className="mt-4 grid min-w-0 gap-4">{events.length ? events.map((event) => <div key={`${event.label}-${event.date}`} className="flex min-w-0 gap-3"><span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-violet-600 dark:bg-violet-300" /><div className="min-w-0"><p className="break-words text-sm font-semibold text-slate-800 dark:text-slate-100">{event.label}</p><p className="text-xs text-slate-500 dark:text-slate-400">{new Date(event.date).toLocaleDateString()}</p></div></div>) : <p className="rounded-2xl bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-500 dark:bg-white/5 dark:text-slate-300">{t("dashboard.emptyStates.noActivity")}</p>}</div></section>;
}
