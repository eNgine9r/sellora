"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { NovaPoshtaSettingsCard } from "@/features/integrations/components/nova-poshta-settings-card";
import { useAuth } from "@/hooks/use-auth";
import { safeApiErrorMessage } from "@/services/api";
import { disconnectNovaPoshta, fetchNovaPoshtaSettings, saveNovaPoshtaSettings, testNovaPoshtaConnection } from "@/services/integrations";
import { NovaPoshtaSettingsPayload } from "@/types/integrations";
import { useI18n } from "@/i18n/provider";

export default function IntegrationsSettingsPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspaceId, status } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const enabled = status === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);
  const [message, setMessage] = useState<string | null>(null);
  const settings = useQuery({ queryKey: ["np-settings", workspaceId], queryFn: () => fetchNovaPoshtaSettings(workspaceId), enabled });
  const save = useMutation({ mutationFn: (payload: NovaPoshtaSettingsPayload) => saveNovaPoshtaSettings(workspaceId, payload), onSuccess: () => { setMessage(t("novaPoshta.saveSuccess")); queryClient.invalidateQueries({ queryKey: ["np-settings", workspaceId] }); }, onError: (error) => setMessage(safeApiErrorMessage(error, t("novaPoshta.saveFailed"))) });
  const test = useMutation({ mutationFn: () => testNovaPoshtaConnection(workspaceId), onSuccess: (result) => { setMessage(result.success ? t("novaPoshta.testSuccess") : t("novaPoshta.testFailed")); queryClient.invalidateQueries({ queryKey: ["np-settings", workspaceId] }); }, onError: (error) => setMessage(safeApiErrorMessage(error, t("novaPoshta.testFailed"))) });
  const disconnect = useMutation({ mutationFn: () => disconnectNovaPoshta(workspaceId), onSuccess: () => { setMessage(t("novaPoshta.disconnectSuccess")); queryClient.invalidateQueries({ queryKey: ["np-settings", workspaceId] }); } });
  return <main className="min-h-screen min-w-0 overflow-x-hidden bg-[#F8F7FC] p-4 text-slate-950 sm:p-6"><div className="mx-auto grid min-w-0 max-w-4xl gap-6"><header className="min-w-0 rounded-2xl bg-white p-6 shadow-sm dark:bg-[#15172A] dark:text-white"><p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">{t("settings.label")}</p><h1 className="mt-2 text-3xl font-bold">{t("settings.integrationsTitle")}</h1><p className="mt-1 text-slate-600 dark:text-slate-300">{t("settings.integrationsSubtitle")}</p></header><NovaPoshtaSettingsCard workspaceId={workspaceId} settings={settings.data} message={message} isSaving={save.isPending} isTesting={test.isPending} isDisconnecting={disconnect.isPending} onSave={(payload) => save.mutate(payload)} onTest={() => test.mutate()} onDisconnect={() => disconnect.mutate()} /></div></main>;
}
