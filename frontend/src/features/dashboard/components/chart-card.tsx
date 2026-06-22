import { ReactNode } from "react";

export function ChartCard({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return <section className="min-w-0 overflow-hidden rounded-[20px] border border-slate-100 bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.06)] dark:border-white/10 dark:bg-slate-900 dark:shadow-none"><div className="mb-4 min-w-0"><h2 className="break-words text-lg font-black text-slate-950 dark:text-white">{title}</h2>{subtitle ? <p className="break-words text-sm text-slate-500 dark:text-slate-400">{subtitle}</p> : null}</div>{children}</section>;
}
