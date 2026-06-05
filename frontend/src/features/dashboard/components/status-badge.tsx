export function StatusBadge({ value }: { value: string }) {
  const palette = value === "DELIVERED" || value === "COMPLETED" ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-100" : value === "RETURNED" || value === "CANCELLED" ? "bg-rose-50 text-rose-700 dark:bg-rose-400/15 dark:text-rose-100" : "bg-violet-50 text-violet-700 dark:bg-violet-400/15 dark:text-violet-100";
  return <span className={`inline-flex max-w-full rounded-full px-3 py-1 text-xs font-bold ${palette}`}>{value.replaceAll("_", " ")}</span>;
}
