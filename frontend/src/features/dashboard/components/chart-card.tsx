import { ReactNode } from "react";

export function ChartCard({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return <section className="rounded-[20px] border border-slate-100 bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.06)]"><div className="mb-4"><h2 className="text-lg font-black text-slate-950">{title}</h2>{subtitle ? <p className="text-sm text-slate-500">{subtitle}</p> : null}</div>{children}</section>;
}
