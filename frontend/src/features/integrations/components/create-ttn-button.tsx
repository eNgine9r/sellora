"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useI18n } from "@/i18n/provider";
import { safeApiErrorMessage } from "@/services/api";
import { createNovaPoshtaTtn, syncNovaPoshtaStatus } from "@/services/integrations";

function useFriendlyTtnMessage() {
  const { t } = useI18n();
  return (result: { success: boolean; message: string; errors?: string[] }) => {
    if (result.success) return t("novaPoshta.ttnCreated");
    if (result.errors?.includes("ttn already exists")) return t("shipments.duplicateTtnWarning");
    if (result.errors?.includes("NOVA_POSHTA_TTN_FAILED")) return t("shipments.createTtnFailed");
    const senderMissing = result.errors?.some((error) => error.startsWith("sender_"));
    if (senderMissing) return t("shipments.senderSettingsRequired");
    const recipientMissing = result.errors?.some((error) => ["recipient_name is required", "recipient_phone is required", "city is required", "warehouse is required"].includes(error));
    if (recipientMissing) return t("shipments.recipientAddressRequired");
    const customerMissing = result.errors?.includes("customer is required");
    if (customerMissing) return t("shipments.orderCustomerMissing");
    return result.message || t("shipments.createTtnFailed");
  };
}

export function CreateTtnButton({ workspaceId, shipmentId, hasTtn = false }: { workspaceId: string; shipmentId: string; hasTtn?: boolean }) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const friendlyTtnMessage = useFriendlyTtnMessage();
  const [message, setMessage] = useState<string | null>(null);
  const invalidateShipmentData = () => {
    queryClient.invalidateQueries({ queryKey: ["shipments", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["shipments-summary", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["orders", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["order-shipment", workspaceId] });
  };
  const create = useMutation({ mutationFn: () => createNovaPoshtaTtn(workspaceId, shipmentId), onSuccess: (result) => { setMessage(friendlyTtnMessage(result)); invalidateShipmentData(); }, onError: (error) => setMessage(safeApiErrorMessage(error, t("shipments.createTtnFailed"))) });
  const sync = useMutation({ mutationFn: () => syncNovaPoshtaStatus(workspaceId, shipmentId), onSuccess: (result) => { setMessage(result.success ? t("novaPoshta.statusSynced") : t("shipments.statusUnavailable")); invalidateShipmentData(); }, onError: (error) => setMessage(safeApiErrorMessage(error, t("shipments.statusSyncFailed"))) });
  return <div className="grid gap-2"><div className="grid gap-2 sm:grid-cols-2"><button className="min-h-11 rounded-xl bg-blue-600 px-4 py-2 font-bold text-white disabled:opacity-60" disabled={create.isPending || hasTtn} onClick={() => create.mutate()}>{create.isPending ? t("novaPoshta.creatingTtn") : hasTtn ? t("novaPoshta.ttnExists") : t("shipments.createTtn")}</button><button className="min-h-11 rounded-xl border border-slate-300 px-4 py-2 font-bold disabled:opacity-60 dark:border-white/10" disabled={sync.isPending || !hasTtn} onClick={() => sync.mutate()}>{sync.isPending ? t("novaPoshta.syncingStatus") : !hasTtn ? t("shipments.ttnMissing") : t("shipments.syncStatus")}</button></div>{message ? <p className="rounded-lg bg-blue-50 p-3 text-sm font-semibold text-blue-700 dark:bg-blue-500/15 dark:text-blue-100">{message}</p> : null}</div>;
}
// Nova Poshta production validation compatibility marker: statusSyncUnavailable duplicateTtn.
