export function TrendBadge({ value }: { value: string }) {
  const positive = !value.startsWith("-");
  return <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-bold ${positive ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-100" : "bg-rose-50 text-rose-700 dark:bg-rose-400/15 dark:text-rose-100"}`}>{positive ? "↗" : "↘"} {value}</span>;
}
