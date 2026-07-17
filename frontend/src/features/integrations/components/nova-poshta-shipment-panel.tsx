"use client";

import { CreateTtnButton } from "@/features/integrations/components/create-ttn-button";
import { TtnDocumentLimitation } from "@/features/shipments/components/ttn-actions";
import { useI18n } from "@/i18n/provider";
import { Shipment } from "@/types/shipments";

export function NovaPoshtaShipmentPanel({ workspaceId, shipment }: { workspaceId: string; shipment: Shipment }) {
  const { t } = useI18n();
  if (shipment.carrier !== "NOVA_POSHTA") return null;
  const trackingNumber = shipment.nova_poshta_document_number || shipment.tracking_number;
  const hasTtn = Boolean(trackingNumber || shipment.nova_poshta_document_ref);
  const missingRecipient = !shipment.recipient_name || !shipment.recipient_phone || !shipment.city || !shipment.warehouse;
  return (
    <section className="grid gap-3 rounded-xl bg-slate-50 p-3 text-sm dark:bg-white/[0.04]" data-nova-poshta-provider-panel>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h3 className="font-bold text-slate-950 dark:text-white">{t("shipments.novaPoshtaSection")}</h3>
        <span className={`rounded-full px-3 py-1 text-xs font-bold ${hasTtn ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-100" : shipment.nova_poshta_manual_reconciliation_required ? "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-100" : "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-100"}`}>{hasTtn ? t("novaPoshta.ttnExists") : t("shipments.ttnMissing")}</span>
      </div>
      {missingRecipient ? <p className="rounded-lg bg-amber-50 p-2 text-xs font-semibold text-amber-800 dark:bg-amber-500/15 dark:text-amber-100">{t("shipments.recipientAddressRequired")}</p> : null}
      <div className="grid grid-cols-2 gap-2">
        <span className="text-slate-500 dark:text-slate-400">{t("novaPoshta.cityRef")}</span><strong className="break-all">{shipment.nova_poshta_city_ref ? t("common.yes") : "—"}</strong>
        <span className="text-slate-500 dark:text-slate-400">{t("novaPoshta.warehouseRef")}</span><strong className="break-all">{shipment.nova_poshta_warehouse_ref ? t("common.yes") : "—"}</strong>
        <span className="text-slate-500 dark:text-slate-400">{t("novaPoshta.documentRef")}</span><strong className="break-all">{shipment.nova_poshta_document_ref ? t("common.yes") : "—"}</strong>
        <span className="text-slate-500 dark:text-slate-400">{t("novaPoshta.documentNumber")}</span><strong>{trackingNumber ?? "—"}</strong>
        <span className="text-slate-500 dark:text-slate-400">{t("shipments.novaPoshtaStatus")}</span><strong>{shipment.nova_poshta_raw_status ?? shipment.external_status ?? t("novaPoshta.statusSyncUnavailableShort")}</strong>
        <span className="text-slate-500 dark:text-slate-400">{t("shipments.lastSynced")}</span><strong>{shipment.nova_poshta_synced_at ? new Date(shipment.nova_poshta_synced_at).toLocaleString() : "—"}</strong>
      </div>
      <p className="rounded-lg bg-blue-50 p-2 text-xs font-semibold text-blue-800 dark:bg-blue-500/15 dark:text-blue-100">{hasTtn ? t("novaPoshta.statusSyncNote") : t("shipments.createTtnReadinessHint")}</p>
      <CreateTtnButton workspaceId={workspaceId} shipmentId={shipment.id} hasTtn={hasTtn} manualReconciliationRequired={shipment.nova_poshta_manual_reconciliation_required} />
      <TtnDocumentLimitation />
    </section>
  );
}
