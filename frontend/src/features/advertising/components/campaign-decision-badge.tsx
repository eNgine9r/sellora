import type { DecisionStatus } from "@/features/advertising/lib/decision-support";

const STATUS_STYLES: Record<DecisionStatus, string> = {
  GOOD: "border-emerald-200 bg-emerald-50 text-emerald-800",
  WATCH: "border-amber-200 bg-amber-50 text-amber-800",
  PROBLEM: "border-rose-200 bg-rose-50 text-rose-800",
  NO_DATA: "border-slate-200 bg-slate-50 text-slate-600",
};

export function CampaignDecisionBadge({ label, status }: { label: string; status: DecisionStatus }) {
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-bold ${STATUS_STYLES[status]}`}>{label}</span>;
}
