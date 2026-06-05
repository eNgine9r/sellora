"use client";

import { useI18n } from "@/i18n/provider";
import { statusBadgeClass, StatusTone } from "@/lib/status-styles";

function toneForStatus(value: string): StatusTone { if (value === "DELIVERED" || value === "COMPLETED" || value === "PAID" || value === "ACTIVE") return "success"; if (value === "RETURNED" || value === "CANCELLED" || value === "FAILED") return "danger"; if (value === "SHIPPED" || value === "IN_TRANSIT") return "violet"; if (value === "CONFIRMED" || value === "ARRIVED") return "warning"; return "info"; }
function groupForStatus(value: string) { if (["PENDING", "PAID", "COD", "REFUNDED", "PARTIALLY_PAID", "FAILED"].includes(value)) return "payment"; if (["DRAFT", "CREATED", "IN_TRANSIT", "ARRIVED"].includes(value)) return "shipment"; return "order"; }

export function StatusBadge({ value }: { value: string }) {
  const { formatStatus } = useI18n();
  return <span className={statusBadgeClass(toneForStatus(value))}>{formatStatus(groupForStatus(value), value)}</span>;
}
