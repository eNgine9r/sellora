"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import { Shipment, ShipmentStatus } from "@/types/shipments";
import { NovaPoshtaShipmentPanel } from "@/features/integrations/components/nova-poshta-shipment-panel";
import { ShipmentStatusBadge } from "./shipment-status-badge";
import { CopyTtnButton, TtnDocumentLimitation } from "./ttn-actions";

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

function Section({ title, children }: { title: string; children: ReactNode }) {
  return <section className="grid gap-3 rounded-2xl border border-slate-100 p-4 dark:border-white/10"><h3 className="font-bold text-slate-950 dark:text-white">{title}</h3>{children}</section>;
}

export function ShipmentDetails({ shipment, workspaceId, onStatusChange }: { shipment: Shipment; workspaceId: string; onStatusChange: (status: ShipmentStatus) => void }) {
  const { t, formatStatus } = useI18n();
  const hasProviderDocument = Boolean(shipment.nova_poshta_document_ref || shipment.nova_poshta_document_number);
  const actions = NEXT_ACTIONS[shipment.status];
  const trackingNumber = shipment.nova_poshta_document_number ?? shipment.tracking_number;
  return (
    <div className="grid min-w-0 gap-5">
      <div className="flex min-w-0 flex-col gap-3 border-b border-slate-100 pb-4 dark:border-white/10 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0"><p className="text-sm font-bold uppercase tracking-[0.2em] text-blue-600 dark:text-blue-300">{t("shipments.details")}</p><h2 className="mt-2 max-w-full break-words text-2xl font-black leading-tight text-slate-950 dark:text-white">{trackingNumber ?? t("shipments.draftShipment")}</h2></div>
        <ShipmentStatusBadge status={shipment.status} />
      </div>

      <Section title={t("shipments.orderSection")}>
        <div className="grid gap-3 sm:grid-cols-2">
          <DetailRow label={t("shipments.order")} value={shipment.order_number} />
          <DetailRow label={t("orders.changeStatus")} value={shipment.order_status ? formatStatus("order", shipment.order_status as never) : null} />
          <DetailRow label={t("tables.payment")} value={shipment.order_payment_status ? formatStatus("payment", shipment.order_payment_status as never) : null} />
          <DetailRow label={t("analytics.revenue")} value={shipment.order_total ? formatMoney(shipment.order_total) : null} />
        </div>
        <Link className="inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-300 px-4 py-2 text-sm font-bold dark:border-white/10" href={`/orders?order_id=${shipment.order_id}`}>{t("shipments.openOrder")}</Link>
      </Section>

      <Section title={t("shipments.customerSection")}>
        {shipment.customer_id ? <div className="grid gap-3 sm:grid-cols-2"><DetailRow label={t("shipments.customer")} value={shipment.customer_name} /><DetailRow label={t("shipments.phone")} value={shipment.customer_phone} /><DetailRow label={t("customers.instagram")} value={shipment.customer_instagram_username ? `@${shipment.customer_instagram_username.replace(/^@/, "")}` : null} /></div> : <p className="rounded-xl bg-amber-50 p-3 text-sm font-semibold text-amber-800 dark:bg-amber-500/15 dark:text-amber-100">{t("shipments.orderCustomerMissingUpdate")}</p>}
      </Section>

      <Section title={t("shipments.recipientSection")}>
        <div className="grid gap-3 sm:grid-cols-2"><DetailRow label={t("shipments.recipientName")} value={shipment.recipient_name} /><DetailRow label={t("shipments.recipientPhone")} value={shipment.recipient_phone} /><DetailRow label={t("shipments.city")} value={shipment.city} /><DetailRow label={t("shipments.warehouse")} value={shipment.warehouse} /></div>
      </Section>

      <Section title={t("shipments.trackingSection")}>
        <div className="grid gap-3 sm:grid-cols-2"><DetailRow label={t("shipments.carrier")} value={shipment.carrier} /><DetailRow label={t("shipments.trackingTtn")} value={trackingNumber} /><DetailRow label={t("novaPoshta.documentRef")} value={shipment.nova_poshta_document_ref ? t("common.yes") : null} /><DetailRow label={t("shipments.externalStatus")} value={shipment.nova_poshta_raw_status ?? shipment.external_status} /><DetailRow label={t("shipments.lastSynced")} value={shipment.nova_poshta_synced_at ? new Date(shipment.nova_poshta_synced_at).toLocaleString() : null} /><DetailRow label={t("shipments.updated")} value={new Date(shipment.updated_at).toLocaleString()} /></div>
        <div className="grid gap-2 sm:grid-cols-2"><CopyTtnButton trackingNumber={trackingNumber} variant="primary" /></div>
        <TtnDocumentLimitation />
      </Section>

      <Section title={t("shipments.statusSection")}>
        <div className="flex flex-wrap items-center gap-3"><ShipmentStatusBadge status={shipment.status} />{shipment.external_status ? <span className="rounded-full bg-slate-100 px-3 py-2 text-sm font-semibold text-slate-700 dark:bg-white/10 dark:text-slate-100">{t("shipments.novaPoshtaStatus")}: {shipment.external_status}</span> : <span className="text-sm text-slate-500 dark:text-slate-400">{t("novaPoshta.statusSyncUnavailableShort")}</span>}</div>
        <div className="grid gap-2 rounded-2xl bg-slate-50 p-4 text-sm text-slate-600 dark:bg-white/[0.05] dark:text-slate-300"><span>{t("shipments.shipped")}: {shipment.shipped_at ? new Date(shipment.shipped_at).toLocaleString() : "—"}</span><span>{t("shipments.delivered")}: {shipment.delivered_at ? new Date(shipment.delivered_at).toLocaleString() : "—"}</span><span>{t("shipments.returned")}: {shipment.returned_at ? new Date(shipment.returned_at).toLocaleString() : "—"}</span></div>
      </Section>

      {shipment.notes ? <p className="rounded-2xl bg-slate-50 p-4 text-sm leading-6 text-slate-600 dark:bg-white/[0.05] dark:text-slate-300">{shipment.notes}</p> : null}
      <NovaPoshtaShipmentPanel workspaceId={workspaceId} shipment={shipment} />
      {hasProviderDocument ? <p className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm font-semibold text-amber-900 dark:border-amber-400/30 dark:bg-amber-500/15 dark:text-amber-100">{t("shipments.archiveNpDescription")}</p> : null}
      {actions.length ? <div className="grid gap-2 sm:grid-cols-2">{actions.map((status) => <button key={status} className="min-h-11 rounded-xl border border-slate-300 px-4 py-3 text-sm font-bold hover:bg-slate-50 dark:border-white/10 dark:text-slate-100 dark:hover:bg-white/10" onClick={() => onStatusChange(status)}>{formatStatus("shipment", status)}</button>)}</div> : <p className="text-sm text-slate-500 dark:text-slate-400">{t("shipments.noNextActions")}</p>}
    </div>
  );
}
