import { ReactNode } from "react";
import { TrendBadge } from "./trend-badge";

export function KpiCard({ label, value, helper, trend, icon }: { label: string; value: ReactNode; helper?: string; trend?: string; icon?: ReactNode }) {
  return <article className="rounded-[20px] border border-slate-100 bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.06)] transition hover:-translate-y-0.5 hover:shadow-[0_22px_55px_rgba(109,40,217,0.12)]"><div className="flex items-start justify-between gap-3"><div><p className="text-sm font-semibold text-slate-500">{label}</p><div className="mt-3 text-3xl font-black tracking-tight text-slate-950">{value}</div></div><div className="rounded-2xl bg-violet-50 p-3 text-violet-700">{icon ?? "✦"}</div></div><div className="mt-4 flex items-center justify-between gap-3 text-sm"><span className="text-slate-500">{helper ?? "За поточний період"}</span>{trend ? <TrendBadge value={trend} /> : null}</div></article>;
}
