import { LeadStatus } from "@/types/crm";

const STATUS_STYLES: Record<LeadStatus, string> = {
  NEW: "bg-blue-100 text-blue-700",
  IN_PROGRESS: "bg-amber-100 text-amber-700",
  QUALIFIED: "bg-emerald-100 text-emerald-700",
  CONVERTED: "bg-purple-100 text-purple-700",
  LOST: "bg-rose-100 text-rose-700",
};

export function LeadStatusBadge({ status }: { status: LeadStatus }) {
  return <span className={`rounded-full px-3 py-1 text-xs font-semibold ${STATUS_STYLES[status]}`}>{status.replace("_", " ")}</span>;
}
