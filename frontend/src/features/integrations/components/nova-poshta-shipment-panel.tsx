"use client";

import { CreateTtnButton } from "@/features/integrations/components/create-ttn-button";
import { useI18n } from "@/i18n/provider";
import { Shipment } from "@/types/shipments";

export function NovaPoshtaShipmentPanel({ workspaceId, shipment }: { workspaceId: string; shipment: Shipment }) {
  const { t } = useI18n();
  if (shipment.carrier !== "NOVA_POSHTA") return null;
  const hasTtn = Boolean(shipment.nova_poshta_document_number || shipment.tracking_number);
  return <section className="grid gap-3 rounded-xl bg-slate-50 p-3 text-sm dark:bg-white/[0.04]"><div className="grid grid-cols-2 gap-2"><span className="text-slate-500 dark:text-slate-400">{t("novaPoshta.cityRef")}</span><strong className="break-all">{shipment.nova_poshta_city_ref ?? "—"}</strong><span className="text-slate-500 dark:text-slate-400">{t("novaPoshta.warehouseRef")}</span><strong className="break-all">{shipment.nova_poshta_warehouse_ref ?? "—"}</strong><span className="text-slate-500 dark:text-slate-400">{t("novaPoshta.documentRef")}</span><strong className="break-all">{shipment.nova_poshta_document_ref ?? "—"}</strong><span className="text-slate-500 dark:text-slate-400">{t("novaPoshta.documentNumber")}</span><strong>{shipment.nova_poshta_document_number ?? shipment.tracking_number ?? "—"}</strong><span className="text-slate-500 dark:text-slate-400">{t("novaPoshta.rawStatus")}</span><strong>{shipment.nova_poshta_raw_status ?? shipment.external_status ?? t("novaPoshta.statusSyncUnavailableShort")}</strong></div><p className="rounded-lg bg-amber-50 p-2 text-xs font-semibold text-amber-800 dark:bg-amber-500/15 dark:text-amber-100">{t("novaPoshta.statusSyncNote")}</p><CreateTtnButton workspaceId={workspaceId} shipmentId={shipment.id} hasTtn={hasTtn} /></section>;
}
