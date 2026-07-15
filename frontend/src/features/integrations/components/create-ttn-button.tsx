"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useI18n } from "@/i18n/provider";
import { safeApiErrorMessage } from "@/services/api";
import { createNovaPoshtaTtn, reconcileNovaPoshtaTtn, syncNovaPoshtaStatus } from "@/services/integrations";
import type { NovaPoshtaActionResponse } from "@/types/integrations";

function useFriendlyTtnMessage() {
  const { t } = useI18n();
  return (result: NovaPoshtaActionResponse) => {
    if (result.success && result.reused_existing_result) return t("shipments.duplicateTtnWarning");
    if (result.success) return t("novaPoshta.ttnCreated");
    if (result.errors?.includes("ttn already exists")) return t("shipments.duplicateTtnWarning");
    if (result.errors?.includes("NOVA_POSHTA_PROVIDER_WRITES_DISABLED")) return result.message;
    if (result.manual_reconciliation_required || result.blind_retry_blocked) return t("shipments.createTtnIncomplete");
    if (result.errors?.includes("NOVA_POSHTA_TTN_FAILED")) return t("shipments.createTtnFailed");
    if (result.errors?.includes("NOVA_POSHTA_TTN_INCOMPLETE")) return t("shipments.createTtnIncomplete");
    const senderMissing = result.errors?.some((error) => error.startsWith("sender_"));
    if (senderMissing) return t("shipments.senderSettingsRequired");
    if (result.errors?.includes("recipient_phone is required")) return t("shipments.recipientPhoneRequired");
    if (result.errors?.includes("city is required")) return t("shipments.recipientCityRequired");
    if (result.errors?.includes("warehouse is required")) return t("shipments.recipientWarehouseRequired");
    const recipientMissing = result.errors?.some((error) => ["recipient_name is required", "recipient_phone is required", "city is required", "warehouse is required"].includes(error));
    if (recipientMissing) return t("shipments.recipientAddressRequired");
    if (result.errors?.includes("customer is required")) return t("shipments.orderCustomerMissing");
    return result.message || t("shipments.createTtnFailed");
  };
}

export function CreateTtnButton({ workspaceId, shipmentId, hasTtn = false, manualReconciliationRequired = false }: { workspaceId: string; shipmentId: string; hasTtn?: boolean; manualReconciliationRequired?: boolean }) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const friendlyTtnMessage = useFriendlyTtnMessage();
  const createInFlight = useRef(false);
  const reconcileInFlight = useRef(false);
  const [message, setMessage] = useState<string | null>(manualReconciliationRequired ? t("shipments.createTtnIncomplete") : null);
  const [manualHold, setManualHold] = useState(manualReconciliationRequired);
  const invalidateShipmentData = () => {
    queryClient.invalidateQueries({ queryKey: ["shipments", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["shipments-summary", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["orders", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["order-shipment", workspaceId] });
  };
  const applyResult = (result: NovaPoshtaActionResponse) => {
    setMessage(friendlyTtnMessage(result));
    setManualHold(Boolean(result.manual_reconciliation_required || result.blind_retry_blocked));
    invalidateShipmentData();
  };
  const create = useMutation({ mutationFn: () => createNovaPoshtaTtn(workspaceId, shipmentId), onSuccess: applyResult, onError: (error) => setMessage(safeApiErrorMessage(error, t("shipments.createTtnFailed"))) });
  const reconcile = useMutation({ mutationFn: () => reconcileNovaPoshtaTtn(workspaceId, shipmentId), onSuccess: applyResult, onError: (error) => setMessage(safeApiErrorMessage(error, t("shipments.statusSyncFailed"))) });
  const sync = useMutation({ mutationFn: () => syncNovaPoshtaStatus(workspaceId, shipmentId), onSuccess: (result) => { setMessage(result.manual_review_required ? result.message : result.success ? t("novaPoshta.statusSynced") : t("shipments.statusUnavailable")); invalidateShipmentData(); }, onError: (error) => setMessage(safeApiErrorMessage(error, t("shipments.statusSyncFailed"))) });

  const submitCreate = () => {
    if (createInFlight.current || create.isPending || hasTtn || manualHold) return;
    createInFlight.current = true;
    create.mutate(undefined, { onSettled: () => { createInFlight.current = false; } });
  };
  const submitReconcile = () => {
    if (reconcileInFlight.current || reconcile.isPending) return;
    reconcileInFlight.current = true;
    reconcile.mutate(undefined, { onSettled: () => { reconcileInFlight.current = false; } });
  };

  return <div className="grid gap-2">
    {manualHold ? <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm font-semibold text-amber-900 dark:border-amber-400/30 dark:bg-amber-500/15 dark:text-amber-100" role="alert" data-nova-poshta-manual-reconciliation>{message ?? t("shipments.createTtnIncomplete")}</div> : null}
    <div className="grid gap-2 sm:grid-cols-2">
      <button aria-busy={create.isPending} className="min-h-11 rounded-xl bg-blue-600 px-4 py-2 font-bold text-white disabled:opacity-60" disabled={create.isPending || createInFlight.current || hasTtn || manualHold} onClick={submitCreate}>{create.isPending ? t("novaPoshta.creatingTtn") : hasTtn ? t("novaPoshta.ttnExists") : t("shipments.createTtn")}</button>
      {manualHold && !hasTtn ? <button aria-busy={reconcile.isPending} className="min-h-11 rounded-xl border border-amber-400 px-4 py-2 font-bold text-amber-800 disabled:opacity-60 dark:text-amber-100" disabled={reconcile.isPending || reconcileInFlight.current} onClick={submitReconcile}>{reconcile.isPending ? t("common.loading") : t("actions.retry")}</button> : <button className="min-h-11 rounded-xl border border-slate-300 px-4 py-2 font-bold disabled:opacity-60 dark:border-white/10" disabled={sync.isPending || !hasTtn} onClick={() => sync.mutate()}>{sync.isPending ? t("novaPoshta.syncingStatus") : !hasTtn ? t("shipments.ttnMissing") : t("shipments.syncStatus")}</button>}
    </div>
    {!manualHold && message ? <p className="rounded-lg bg-blue-50 p-3 text-sm font-semibold text-blue-700 dark:bg-blue-500/15 dark:text-blue-100">{message}</p> : null}
  </div>;
}
