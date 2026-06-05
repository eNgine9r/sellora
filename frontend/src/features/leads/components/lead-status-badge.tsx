import { statusBadgeClass, StatusTone } from "@/lib/status-styles";
import { LeadStatus } from "@/types/crm";

const STATUS_TONES: Record<LeadStatus, StatusTone> = {
  NEW: "info",
  IN_PROGRESS: "warning",
  QUALIFIED: "success",
  CONVERTED: "violet",
  LOST: "danger",
};

export function LeadStatusBadge({ status }: { status: LeadStatus }) {
  return <span className={statusBadgeClass(STATUS_TONES[status])}>{status.replace("_", " ")}</span>;
}
