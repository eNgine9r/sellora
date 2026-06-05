"use client";

import { useI18n } from "@/i18n/provider";
import { Shipment, ShipmentStatus } from "@/types/shipments";
import { NovaPoshtaShipmentPanel } from "@/features/integrations/components/nova-poshta-shipment-panel";
import { ShipmentStatusBadge } from "./shipment-status-badge";

const NEXT_ACTIONS: Record<ShipmentStatus, ShipmentStatus[]> = {
  DRAFT: ["CREATED", "CANCELLED"],
  CREATED: ["IN_TRANSIT", "CANCELLED"],
  IN_TRANSIT: ["ARRIVED", "DELIVERED", "RETURNED"],
  ARRIVED: ["DELIVERED", "RETURNED"],
  DELIVERED: ["RETURNED"],
  RETURNED: [],
  CANCELLED: [],
};

function DetailRow({ label, value }: { label: string; value: string | number | null | undefined }) {
  return <div className="grid min-w-0 gap-1 rounded-2xl bg-slate-50 px-4 py-3 dark:bg-white/[0.05]"><span className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">{label}</span><strong className="min-w-0 break-words text-sm text-slate-950 dark:text-white">{value ?? "—"}</strong></div>;
}

export function ShipmentDetails({ shipment, workspaceId, onStatusChange }: { shipment: Shipment; workspaceId: string; onStatusChange: (status: ShipmentStatus) => void }) {
  const { t, formatStatus } = useI18n();
  const actions = NEXT_ACTIONS[shipment.status];
  return (
    <aside className="grid min-w-0 gap-5 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-slate-900 sm:p-6">
      <div className="flex min-w-0 flex-col gap-3 border-b border-slate-100 pb-4 dark:border-white/10 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0"><p className="text-sm font-bold uppercase tracking-[0.2em] text-blue-600 dark:text-blue-300">{t("shipments.details")}</p><h2 className="mt-2 max-w-full break-words text-2xl font-black leading-tight text-slate-950 dark:text-white">{shipment.tracking_number ?? t("shipments.draftShipment")}</h2></div>
        <ShipmentStatusBadge status={shipment.status} />
      </div>
      <div className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
        <DetailRow label={t("shipments.order")} value={shipment.order_number} />
        <DetailRow label={t("shipments.customer")} value={shipment.customer_name} />
        <DetailRow label={t("shipments.carrier")} value={shipment.carrier} />
        <DetailRow label={t("shipments.city")} value={shipment.city} />
        <DetailRow label={t("shipments.warehouse")} value={shipment.warehouse} />
        <DetailRow label={t("shipments.shipping")} value={shipment.shipping_cost} />
        <DetailRow label={t("shipments.cod")} value={shipment.cod_amount} />
        <DetailRow label={t("tables.created")} value={new Date(shipment.created_at).toLocaleDateString()} />
      </div>
      <div className="grid gap-2 rounded-2xl border border-slate-100 p-4 text-sm text-slate-600 dark:border-white/10 dark:text-slate-300">
        <span>{t("shipments.shipped")}: {shipment.shipped_at ? new Date(shipment.shipped_at).toLocaleString() : "—"}</span>
        <span>{t("shipments.delivered")}: {shipment.delivered_at ? new Date(shipment.delivered_at).toLocaleString() : "—"}</span>
        <span>{t("shipments.returned")}: {shipment.returned_at ? new Date(shipment.returned_at).toLocaleString() : "—"}</span>
      </div>
      {shipment.notes ? <p className="rounded-2xl bg-slate-50 p-4 text-sm leading-6 text-slate-600 dark:bg-white/[0.05] dark:text-slate-300">{shipment.notes}</p> : null}
      <NovaPoshtaShipmentPanel workspaceId={workspaceId} shipment={shipment} />
      {actions.length ? <div className="grid gap-2 sm:grid-cols-2">{actions.map((status) => <button key={status} className="min-h-11 rounded-xl border border-slate-300 px-4 py-3 text-sm font-bold hover:bg-slate-50 dark:border-white/10 dark:text-slate-100 dark:hover:bg-white/10" onClick={() => onStatusChange(status)}>{formatStatus("shipment", status)}</button>)}</div> : <p className="text-sm text-slate-500 dark:text-slate-400">{t("shipments.noNextActions")}</p>}
    </aside>
  );
}
