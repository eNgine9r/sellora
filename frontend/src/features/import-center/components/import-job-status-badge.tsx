import { statusBadgeClass, StatusTone } from "@/lib/status-styles";
import { ImportJobStatus } from "@/types/import-center";

function toneForStatus(status: string): StatusTone {
  if (["COMPLETED", "EXECUTED"].includes(status)) return "success";
  if (["FAILED", "ERROR"].includes(status)) return "danger";
  if (["VALIDATED", "DRY_RUN"].includes(status)) return "warning";
  return "info";
}

export function ImportJobStatusBadge({ status }: { status?: ImportJobStatus | string }) { if (!status) return null; return <span className={statusBadgeClass(toneForStatus(String(status)))}>{status}</span>; }
