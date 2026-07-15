"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { WorkspacePage, WorkspaceHeader } from "@/components/crm-workspace";
import { MetaAdsReadinessCard } from "@/features/integrations/components/meta-ads-readiness-card";
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
  return <WorkspacePage><WorkspaceHeader eyebrow={t("settings.label")} title={t("settings.integrationsTitle")} description={t("settings.integrationsSubtitle")} /><section className="grid min-w-0 gap-4 xl:grid-cols-2"><MetaAdsReadinessCard /><NovaPoshtaSettingsCard workspaceId={workspaceId} settings={settings.data} message={message} isSaving={save.isPending} isTesting={test.isPending} isDisconnecting={disconnect.isPending} onSave={(payload) => save.mutate(payload)} onTest={() => test.mutate()} onDisconnect={() => disconnect.mutate()} /></section></WorkspacePage>;
}
