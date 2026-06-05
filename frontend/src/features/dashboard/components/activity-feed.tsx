"use client";
import { useI18n } from "@/i18n/provider";
export function ActivityFeed() {
  const { t } = useI18n();
  const events = [t("orders.create"), t("customers.create"), t("importCenter.dryRun")];
  return <section className="min-w-0 rounded-[20px] border border-slate-100 bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.06)] dark:border-white/10 dark:bg-slate-900 dark:shadow-none"><h2 className="text-lg font-black text-slate-950 dark:text-white">{t("dashboard.activity")}</h2><div className="mt-4 grid min-w-0 gap-4">{events.map((event) => <div key={event} className="flex min-w-0 gap-3"><span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-violet-600 dark:bg-violet-300" /><div className="min-w-0"><p className="break-words text-sm font-semibold text-slate-800 dark:text-slate-100">{event}</p><p className="text-xs text-slate-500 dark:text-slate-400">{t("topbar.dateToday")}</p></div></div>)}</div></section>;
}
