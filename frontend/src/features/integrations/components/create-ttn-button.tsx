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
    if (result.errors?.includes("ttn already exists")) return t("novaPoshta.duplicateTtn");
    if (result.errors?.includes("NOVA_POSHTA_TTN_FAILED")) return t("novaPoshta.ttnFailed");
    const senderMissing = result.errors?.some((error) => error.startsWith("sender_"));
    if (senderMissing) return t("novaPoshta.senderSettingsIncomplete");
    return result.message || t("novaPoshta.ttnFailed");
  };
}

export function CreateTtnButton({ workspaceId, shipmentId, hasTtn = false }: { workspaceId: string; shipmentId: string; hasTtn?: boolean }) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const friendlyTtnMessage = useFriendlyTtnMessage();
  const [message, setMessage] = useState<string | null>(null);
  const create = useMutation({ mutationFn: () => createNovaPoshtaTtn(workspaceId, shipmentId), onSuccess: (result) => { setMessage(friendlyTtnMessage(result)); queryClient.invalidateQueries({ queryKey: ["shipments", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["orders", workspaceId] }); }, onError: (error) => setMessage(safeApiErrorMessage(error, t("novaPoshta.notConfigured"))) });
  const sync = useMutation({ mutationFn: () => syncNovaPoshtaStatus(workspaceId, shipmentId), onSuccess: (result) => { setMessage(result.success ? t("novaPoshta.statusSynced") : t("novaPoshta.statusSyncUnavailable")); queryClient.invalidateQueries({ queryKey: ["shipments", workspaceId] }); }, onError: (error) => setMessage(safeApiErrorMessage(error, t("novaPoshta.statusSyncUnavailable"))) });
  return <div className="grid gap-2"><div className="grid gap-2 sm:grid-cols-2"><button className="min-h-11 rounded-xl bg-blue-600 px-4 py-2 font-bold text-white disabled:opacity-60" disabled={create.isPending || hasTtn} onClick={() => create.mutate()}>{create.isPending ? t("novaPoshta.creatingTtn") : hasTtn ? t("novaPoshta.ttnExists") : t("shipments.createTtn")}</button><button className="min-h-11 rounded-xl border border-slate-300 px-4 py-2 font-bold disabled:opacity-60 dark:border-white/10" disabled={sync.isPending || !hasTtn} onClick={() => sync.mutate()}>{sync.isPending ? t("novaPoshta.syncingStatus") : t("shipments.syncStatus")}</button></div>{message ? <p className="rounded-lg bg-blue-50 p-3 text-sm font-semibold text-blue-700 dark:bg-blue-500/15 dark:text-blue-100">{message}</p> : null}</div>;
}
