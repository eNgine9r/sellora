"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { WorkspacePage, WorkspaceHeader } from "@/components/crm-workspace";
import { MetaAdsReadinessCard } from "@/features/integrations/components/meta-ads-readiness-card";
import { NovaPoshtaSettingsCard } from "@/features/integrations/components/nova-poshta-settings-card";
import { useAuth } from "@/hooks/use-auth";
import { safeApiErrorMessage } from "@/services/api";
import {
  disconnectNovaPoshta,
  fetchNovaPoshtaSettings,
  saveNovaPoshtaSettings,
  testNovaPoshtaConnection,
  updateNovaPoshtaWritePermission,
} from "@/services/integrations";
import type { NovaPoshtaSettingsPayload } from "@/types/integrations";
import { useI18n } from "@/i18n/provider";

export default function IntegrationsSettingsPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspaceId, status } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const enabled = status === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);
  const [message, setMessage] = useState<string | null>(null);
  const settings = useQuery({ queryKey: ["np-settings", workspaceId], queryFn: () => fetchNovaPoshtaSettings(workspaceId), enabled });

  const connectionTestMessage = (result: { success: boolean; errors: string[] }) => {
    if (result.success) return t("novaPoshta.testSuccess");
    const errorCode = result.errors[0];
    const localizedErrors: Record<string, string> = {
      NOVA_POSHTA_API_KEY_INVALID: t("novaPoshta.testErrors.apiKeyInvalid"),
      NOVA_POSHTA_SENDER_VALIDATION_UNAVAILABLE: t("novaPoshta.testErrors.senderValidationUnavailable"),
      NOVA_POSHTA_SENDER_PHONE_INVALID: t("novaPoshta.testErrors.senderPhoneInvalid"),
      NOVA_POSHTA_SENDER_COUNTERPARTY_INVALID: t("novaPoshta.testErrors.senderCounterpartyInvalid"),
      NOVA_POSHTA_SENDER_CONTACT_INVALID: t("novaPoshta.testErrors.senderContactInvalid"),
      NOVA_POSHTA_SENDER_ADDRESS_INVALID: t("novaPoshta.testErrors.senderAddressInvalid"),
      NOVA_POSHTA_SENDER_CITY_MISMATCH: t("novaPoshta.testErrors.senderCityMismatch"),
    };
    return localizedErrors[errorCode] ?? t("novaPoshta.testFailed");
  };

  const invalidateNovaPoshta = () => Promise.all([
    queryClient.invalidateQueries({ queryKey: ["np-settings", workspaceId] }),
    queryClient.invalidateQueries({ queryKey: ["nova-poshta-readiness", workspaceId] }),
  ]);

  const save = useMutation({
    mutationFn: (payload: NovaPoshtaSettingsPayload) => saveNovaPoshtaSettings(workspaceId, payload),
    onSuccess: () => {
      setMessage(t("novaPoshta.saveSuccess"));
      void invalidateNovaPoshta();
    },
    onError: (error) => setMessage(safeApiErrorMessage(error, t("novaPoshta.saveFailed"))),
  });
  const test = useMutation({
    mutationFn: () => testNovaPoshtaConnection(workspaceId),
    onSuccess: (result) => {
      setMessage(connectionTestMessage(result));
      void invalidateNovaPoshta();
    },
    onError: (error) => setMessage(safeApiErrorMessage(error, t("novaPoshta.testFailed"))),
  });
  const permission = useMutation({
    mutationFn: (allowed: boolean) => updateNovaPoshtaWritePermission(workspaceId, allowed),
    onSuccess: (result) => {
      setMessage(t(result.workspace_permission ? "novaPoshta.permissionEnabled" : "novaPoshta.permissionDisabled"));
      void invalidateNovaPoshta();
    },
    onError: (error) => setMessage(safeApiErrorMessage(error, t("novaPoshta.permissionUpdateFailed"))),
  });
  const disconnect = useMutation({
    mutationFn: () => disconnectNovaPoshta(workspaceId),
    onSuccess: () => {
      setMessage(t("novaPoshta.disconnectSuccess"));
      void invalidateNovaPoshta();
    },
    onError: (error) => setMessage(safeApiErrorMessage(error, t("novaPoshta.disconnectFailed"))),
  });

  return (
    <WorkspacePage>
      <WorkspaceHeader eyebrow={t("settings.label")} title={t("settings.integrationsTitle")} description={t("settings.integrationsSubtitle")} />
      <section className="grid min-w-0 gap-4 xl:grid-cols-2">
        <MetaAdsReadinessCard />
        <NovaPoshtaSettingsCard
          workspaceId={workspaceId}
          settings={settings.data}
          message={message}
          isSaving={save.isPending}
          isTesting={test.isPending}
          isUpdatingPermission={permission.isPending}
          isDisconnecting={disconnect.isPending}
          onSave={(payload) => save.mutate(payload)}
          onTest={() => test.mutate()}
          onUpdateWritePermission={(allowed) => permission.mutate(allowed)}
          onDisconnect={() => disconnect.mutate()}
        />
      </section>
    </WorkspacePage>
  );
}
