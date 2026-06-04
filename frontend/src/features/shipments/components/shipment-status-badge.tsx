import { ShipmentStatus } from "@/types/shipments";

const COLORS: Record<ShipmentStatus, string> = {
  DRAFT: "bg-slate-100 text-slate-700",
  CREATED: "bg-blue-50 text-blue-700",
  IN_TRANSIT: "bg-indigo-50 text-indigo-700",
  ARRIVED: "bg-amber-50 text-amber-700",
  DELIVERED: "bg-emerald-50 text-emerald-700",
  RETURNED: "bg-rose-50 text-rose-700",
  CANCELLED: "bg-slate-200 text-slate-600",
};

export function ShipmentStatusBadge({ status }: { status: ShipmentStatus }) {
  return <span className={`rounded-full px-3 py-1 text-xs font-bold ${COLORS[status]}`}>{status.replaceAll("_", " ")}</span>;
}
