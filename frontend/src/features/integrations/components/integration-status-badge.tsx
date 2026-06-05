import { IntegrationStatus } from "@/types/integrations";

const COLORS: Record<IntegrationStatus, string> = { CONNECTED: "bg-emerald-50 text-emerald-700", DISCONNECTED: "bg-slate-100 text-slate-600", ERROR: "bg-rose-50 text-rose-700" };
export function IntegrationStatusBadge({ status }: { status: IntegrationStatus }) { return <span className={`rounded-full px-3 py-1 text-xs font-bold ${COLORS[status]}`}>{status}</span>; }
