"use client";

import { CreateTtnButton } from "@/features/integrations/components/create-ttn-button";
import { useI18n } from "@/i18n/provider";
import { Shipment } from "@/types/shipments";

export function NovaPoshtaShipmentPanel({ workspaceId, shipment }: { workspaceId: string; shipment: Shipment }) {
  const { t } = useI18n();
  if (shipment.carrier !== "NOVA_POSHTA") return null;
  const trackingNumber = shipment.nova_poshta_document_number || shipment.tracking_number;
  const hasTtn = Boolean(trackingNumber || shipment.nova_poshta_document_ref);
  const missingRecipient = !shipment.recipient_name || !shipment.recipient_phone || !shipment.city || !shipment.warehouse;

  return (
    <section className="grid min-w-0 gap-3 rounded-2xl border border-border-subtle bg-surface-1 p-4 text-sm" data-nova-poshta-provider-panel>
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
        <h3 className="font-bold text-text-primary">{t("shipments.novaPoshtaSection")}</h3>
        <span className={`rounded-full px-3 py-1 text-xs font-bold ${hasTtn ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-100" : "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-100"}`}>
          {hasTtn ? t("novaPoshta.ttnExists") : t("shipments.ttnMissing")}
        </span>
      </div>
      {missingRecipient && !hasTtn ? <p className="rounded-xl bg-amber-50 p-3 text-xs font-semibold text-amber-800 dark:bg-amber-500/15 dark:text-amber-100">{t("shipments.recipientAddressRequired")}</p> : null}
      {hasTtn ? (
        <div className="grid min-w-0 gap-2 rounded-xl bg-slate-50 p-3 dark:bg-white/[0.05]">
          <p className="text-xs font-semibold text-text-muted">{t("shipments.novaPoshtaStatus")}</p>
          <p className="min-w-0 break-words text-sm font-semibold text-text-primary">
            {shipment.nova_poshta_raw_status ?? shipment.external_status ?? t("novaPoshta.statusSyncUnavailableShort")}
          </p>
          <p className="text-xs text-text-secondary">
            {t("shipments.lastSynced")}: {shipment.nova_poshta_synced_at ? new Date(shipment.nova_poshta_synced_at).toLocaleString() : "—"}
          </p>
          <p className="text-xs text-text-muted">{t("shipments.autoTrackingHelp")}</p>
        </div>
      ) : <p className="rounded-xl bg-blue-50 p-3 text-xs font-semibold text-blue-800 dark:bg-blue-500/15 dark:text-blue-100">{t("shipments.createTtnReadinessHint")}</p>}
      <CreateTtnButton workspaceId={workspaceId} shipmentId={shipment.id} hasTtn={hasTtn} manualReconciliationRequired={shipment.nova_poshta_manual_reconciliation_required} />
    </section>
  );
}
