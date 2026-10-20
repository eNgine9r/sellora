"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Instagram, ShieldCheck, Unplug } from "lucide-react";
import { Button, FieldGrid, FieldItem, WorkspaceHeader, WorkspacePage } from "@/components/crm-workspace";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";
import { disconnectInstagram, fetchInstagramStatus, startInstagramConnect, subscribeInstagramWebhooks, validateInstagramConnection } from "@/services/meta-instagram";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";

export default function InstagramIntegrationPage() {
  const { t } = useI18n();
  const { currentWorkspace, currentWorkspaceId } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const queryClient = useQueryClient();
  const [browserLink, setBrowserLink] = useState<string | null>(null);
  const canManage = currentWorkspace?.role === "OWNER";
  const statusQuery = useQuery({ queryKey: ["instagram-connection-status", workspaceId], queryFn: fetchInstagramStatus, enabled: Boolean(workspaceId) });
  const connectMutation = useMutation({ mutationFn: startInstagramConnect, onSuccess: (data) => { window.location.href = data.authorization_url; } });
  const browserMutation = useMutation({ mutationFn: startInstagramConnect, onSuccess: (data) => setBrowserLink(data.authorization_url) });
  const validateMutation = useMutation({ mutationFn: validateInstagramConnection, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["instagram-connection-status", workspaceId] }) });
  const disconnectMutation = useMutation({ mutationFn: () => disconnectInstagram(true), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["instagram-connection-status", workspaceId] }) });
  const webhookMutation = useMutation({ mutationFn: subscribeInstagramWebhooks, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["instagram-connection-status", workspaceId] }) });

  const data = statusQuery.data;
  const requiresReconnect = data?.status === "TOKEN_EXPIRED" || data?.status === "RECONNECT_REQUIRED";
  const hasUsableToken = Boolean(data?.token_present && !requiresReconnect && data.status !== "DISCONNECTED");
  const disconnected = data?.status === "DISCONNECTED";
  return <WorkspacePage>
    <WorkspaceHeader eyebrow="Meta Instagram" title={t("instagramSettings.title")} description={t("instagramSettings.description")} actions={canManage ? <div className="flex flex-wrap gap-2"><Button onClick={() => connectMutation.mutate()} disabled={connectMutation.isPending}>{t(requiresReconnect ? "instagramSettings.reconnect" : "instagramSettings.connect")}</Button><Button variant="secondary" onClick={() => browserMutation.mutate()} disabled={browserMutation.isPending}>{t("instagramSettings.browserLinkButton")}</Button></div> : null} />
    {statusQuery.isLoading ? <LoadingSkeleton /> : null}
    {connectMutation.isError ? <ErrorState title={t("instagramSettings.error")} description={t("instagramSettings.errorDescription")} /> : null}
    {webhookMutation.isError ? <ErrorState title={t("instagramSettings.webhookInactive")} description={t("instagramSettings.webhookInactiveExplanation")} /> : null}
    {!statusQuery.isLoading && data && (requiresReconnect || data.status === "DISCONNECTED") ? <section role="status" className="rounded-2xl border border-warning/30 bg-warning/10 p-4 text-sm leading-6 text-text-secondary"><p className="font-black text-text-primary">{t(requiresReconnect ? "instagramSettings.reconnectExplanation" : "instagramSettings.connectionMissingExplanation")}</p><p className="mt-2">{t("instagramSettings.openInBrowserHint")}</p></section> : null}
    {statusQuery.isError ? <ErrorState title={t("instagramSettings.error")} description={t("instagramSettings.errorDescription")} /> : null}
    {!statusQuery.isLoading && !statusQuery.isError && data && !disconnected ? <section className="rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-4 shadow-[var(--shadow-card)]">
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between"><div className="flex items-center gap-3"><Instagram className="h-6 w-6 text-primary" /><div><h2 className="font-black">{data.instagram_username ?? t("instagramSettings.notConnected")}</h2><p className="text-sm text-text-secondary">{t(`instagramSettings.status.${data.status}`)}</p></div></div><span className="rounded-full bg-primary/15 px-3 py-1 text-xs font-black text-primary">{data.token_present ? t("instagramSettings.tokenEncrypted") : t("instagramSettings.noToken")}</span></div>
      <FieldGrid><FieldItem label={t("instagramSettings.accountType")} value={data.instagram_account_type ?? "—"} /><FieldItem label={t("instagramSettings.permissions")} value={data.granted_permissions.join(", ") || "—"} /><FieldItem label={t("instagramSettings.webhooks")} value={data.webhook_active ? t("instagramSettings.webhookActive") : t("instagramSettings.webhookInactive")} /><FieldItem label={t("instagramSettings.confirmedFields")} value={data.confirmed_webhook_fields.map((field) => t(`instagramSettings.fieldLabels.${field}`)).join(", ") || "—"} /><FieldItem label={t("instagramSettings.missingWebhookFields")} value={data.missing_webhook_fields.map((field) => t(`instagramSettings.fieldLabels.${field}`)).join(", ") || "—"} /><FieldItem label={t("instagramSettings.lastWebhook")} value={data.last_webhook_at ?? "—"} /></FieldGrid>
      {canManage ? <div className="mt-4 flex flex-wrap gap-2">{hasUsableToken && !data.webhook_active ? <Button variant="secondary" onClick={() => webhookMutation.mutate()} disabled={webhookMutation.isPending}>{t("instagramSettings.activateWebhook")}</Button> : null}{hasUsableToken ? <Button variant="secondary" onClick={() => validateMutation.mutate()} disabled={validateMutation.isPending}><ShieldCheck className="h-4 w-4" />{t("instagramSettings.validate")}</Button> : null}{hasUsableToken ? <Button variant="danger" onClick={() => { if (window.confirm(t("instagramSettings.disconnectConfirm"))) disconnectMutation.mutate(); }} disabled={disconnectMutation.isPending}><Unplug className="h-4 w-4" />{t("instagramSettings.disconnect")}</Button> : null}</div> : <p className="mt-4 rounded-2xl bg-surface-2 p-3 text-sm text-text-secondary">{t("instagramSettings.readOnly")}</p>}
    </section> : null}
    {!statusQuery.isLoading && !statusQuery.isError && (!data || disconnected) ? <EmptyState title={t("instagramSettings.notConnected")} description={t("instagramSettings.emptyDescription")} /> : null}
  </WorkspacePage>;
}
