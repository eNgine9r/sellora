export function TrendBadge({ value }: { value: string }) {
  const positive = !value.startsWith("-");
  return <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${positive ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"}`}>{positive ? "↗" : "↘"} {value}</span>;
}
