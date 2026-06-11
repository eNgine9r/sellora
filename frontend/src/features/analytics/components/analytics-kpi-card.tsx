export function AnalyticsKpiCard({ label, value, helper }: { label: string; value: string | number; helper?: string }) {
  return <div className="rounded-xl bg-white p-4 shadow-sm"><p className="text-sm text-slate-500">{label}</p><p className="mt-2 text-2xl font-bold text-slate-950">{value}</p>{helper ? <p className="mt-1 text-xs text-slate-500">{helper}</p> : null}</div>;
}
