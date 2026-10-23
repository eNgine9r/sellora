"use client";

import { useQuery } from "@tanstack/react-query";
import { WorkspaceHeader, WorkspacePage } from "@/components/crm-workspace";
import { InstagramMessagingIntegrationCard } from "@/features/integrations/components/instagram-messaging-integration-card";
import { MetaAdsReadinessCard } from "@/features/integrations/components/meta-ads-readiness-card";
import { NovaPoshtaOverviewCard } from "@/features/integrations/components/nova-poshta-overview-card";
import { useAuth } from "@/hooks/use-auth";
import { fetchNovaPoshtaSettings } from "@/services/integrations";
import { useI18n } from "@/i18n/provider";

export default function IntegrationsSettingsPage() {
  const { t } = useI18n();
  const { currentUser, currentWorkspaceId, status } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const enabled = status === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);
  const settings = useQuery({
    queryKey: ["np-settings", workspaceId],
    queryFn: () => fetchNovaPoshtaSettings(workspaceId),
    enabled,
    retry: false,
  });
  return (
    <WorkspacePage>
      <WorkspaceHeader
        eyebrow={t("settings.label")}
        title={t("settings.integrationsTitle")}
        description={t("integrationHub.pageDescription")}
      />
      <section className="grid min-w-0 items-start gap-4 lg:grid-cols-2 xl:grid-cols-3">
        <InstagramMessagingIntegrationCard workspaceId={workspaceId} />
        <NovaPoshtaOverviewCard settings={settings.data} loading={settings.isPending && enabled} error={settings.isError} />
        <MetaAdsReadinessCard />
      </section>
    </WorkspacePage>
  );
}
