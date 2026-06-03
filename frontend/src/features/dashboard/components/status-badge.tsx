export function StatusBadge({ value }: { value: string }) {
  const palette = value === "DELIVERED" || value === "COMPLETED" ? "bg-emerald-50 text-emerald-700" : value === "RETURNED" || value === "CANCELLED" ? "bg-rose-50 text-rose-700" : "bg-violet-50 text-violet-700";
  return <span className={`rounded-full px-3 py-1 text-xs font-bold ${palette}`}>{value.replaceAll("_", " ")}</span>;
}
