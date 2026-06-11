"use client";
import Link from "next/link";
import { useI18n } from "@/i18n/provider";

export type DashboardNotification = { label: string; value: number; href: string };
export function NotificationsCard({ items = [] }: { items?: DashboardNotification[] }) {
  const { t } = useI18n();
  return <section className="min-w-0 rounded-[20px] border border-slate-100 bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.06)] dark:border-white/10 dark:bg-slate-900 dark:shadow-none"><h2 className="text-lg font-black text-slate-950 dark:text-white">{t("dashboard.notifications")}</h2><div className="mt-4 grid min-w-0 gap-3">{items.length ? items.map((item) => <Link key={item.label} href={item.href} className="flex min-w-0 items-center justify-between gap-3 rounded-2xl bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800 transition hover:bg-amber-100 dark:bg-amber-400/15 dark:text-amber-100"><span className="truncate">{item.label}</span><strong>{item.value}</strong></Link>) : <p className="rounded-2xl bg-emerald-50 px-4 py-3 text-sm font-bold text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-100">{t("dashboard.emptyStates.noNotifications")}</p>}</div></section>;
}
