import { statusBadgeClass, StatusTone } from "@/lib/status-styles";

function toneForStatus(value: string): StatusTone {
  if (value === "DELIVERED" || value === "COMPLETED" || value === "PAID" || value === "ACTIVE") return "success";
  if (value === "RETURNED" || value === "CANCELLED" || value === "FAILED") return "danger";
  if (value === "SHIPPED" || value === "IN_TRANSIT") return "violet";
  if (value === "CONFIRMED" || value === "ARRIVED") return "warning";
  return "info";
}

export function StatusBadge({ value }: { value: string }) {
  return <span className={statusBadgeClass(toneForStatus(value))}>{value.replaceAll("_", " ")}</span>;
}
