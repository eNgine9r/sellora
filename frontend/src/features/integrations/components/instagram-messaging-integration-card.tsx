"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Instagram, MessageCircle, ShieldCheck, Unplug } from "lucide-react";
import { Button, Card, StatusBadge } from "@/components/ui/primitives";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { disconnectInstagram, fetchInstagramStatus, startInstagramConnect, validateInstagramConnection } from "@/services/meta-instagram";
import type { InstagramConnectionStatus, InstagramConnectionStatusResponse } from "@/types/meta-instagram";

function statusTone(status: InstagramConnectionStatus | "DISCONNECTED") {
  if (status === "CONNECTED") return "success" as const;
  if (["PERMISSION_MISSING", "TOKEN_EXPIRED", "WEBHOOK_INACTIVE", "RECONNECT_REQUIRED", "PENDING"].includes(status)) return "warning" as const;
  if (status === "FAILED") return "danger" as const;
  return "neutral" as const;
}

function formatDate(value?: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("uk-UA", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function InstagramMessagingIntegrationCard({ workspaceId }: { workspaceId: string }) {
  const { t } = useI18n();
  const { currentWorkspace } = useAuth();
  const queryClient = useQueryClient();
  const canManage = currentWorkspace?.role === "OWNER";
  const canOpenDirect = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";
  const enabled = Boolean(workspaceId);
  const statusQuery = useQuery({ queryKey: ["instagram-connection-status", workspaceId], queryFn: fetchInstagramStatus, enabled });
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["instagram-connection-status", workspaceId] });
  const connectMutation = useMutation({ mutationFn: startInstagramConnect, onSuccess: (data) => { window.location.assign(data.authorization_url); } });
  const validateMutation = useMutation({ mutationFn: validateInstagramConnection, onSuccess: () => void invalidate() });
  const disconnectMutation = useMutation({ mutationFn: () => disconnectInstagram(true), onSuccess: () => void invalidate() });
  const data: InstagramConnectionStatusResponse | undefined = statusQuery.data;
  const status = data?.status ?? "DISCONNECTED";
  const connected = status === "CONNECTED";
  const permissionOk = Boolean(data?.granted_permissions.includes("instagram_business_basic") && data.granted_permissions.includes("instagram_business_manage_messages"));

  return (
    <Card className="relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-1 bg-[linear-gradient(90deg,#f58529,#dd2a7b,#8134af,#515bd4)]" aria-hidden="true" />
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-[linear-gradient(135deg,rgba(245,133,41,0.16),rgba(129,52,175,0.16))] text-primary"><Instagram className="h-6 w-6" /></span>
          <div className="min-w-0">
            <p className="text-xs font-black uppercase tracking-[0.16em] text-text-muted">{t("instagramSettings.hub.eyebrow")}</p>
            <h2 className="mt-1 text-xl font-black text-text-primary">{t("instagramSettings.hub.title")}</h2>
            <p className="mt-2 text-sm leading-6 text-text-secondary">{t("instagramSettings.hub.subtitle")}</p>
          </div>
        </div>
        <StatusBadge tone={statusTone(status)}>{t(`instagramSettings.status.${status}`)}</StatusBadge>
      </div>

      {statusQuery.isLoading ? <div className="mt-4"><LoadingSkeleton /></div> : null}
      {statusQuery.isError ? <div className="mt-4"><ErrorState title={t("instagramSettings.error")} description={t("instagramSettings.profileFailed")} /></div> : null}
      {!statusQuery.isLoading && !statusQuery.isError && !connected ? (
        <div className="mt-5 grid gap-4">
          <EmptyState title={t("instagramSettings.notConnected")} description={t("instagramSettings.hub.emptyDescription")} />
          <div className="rounded-3xl border border-border-subtle bg-surface-2 p-4 text-sm leading-6 text-text-secondary">
            <p className="font-black text-text-primary">{t("instagramSettings.permissionsRequired")}</p>
            <p>instagram_business_basic · instagram_business_manage_messages</p>
            <p className="mt-2">{t("instagramSettings.manualSafety")}</p>
          </div>
        </div>
      ) : null}
      {connected && data ? <ConnectedSummary data={data} permissionOk={permissionOk} /> : null}

      <div className="mt-5 flex flex-wrap gap-2">
        {canManage && !connected ? <Button onClick={() => connectMutation.mutate()} loading={connectMutation.isPending}>{t("instagramSettings.connect")}</Button> : null}
        {canManage && connected ? <Button variant="secondary" onClick={() => validateMutation.mutate()} loading={validateMutation.isPending}><ShieldCheck className="h-4 w-4" />{t("instagramSettings.validate")}</Button> : null}
        {canManage && connected ? <Button variant="danger" onClick={() => { if (window.confirm(t("instagramSettings.disconnectConfirm"))) disconnectMutation.mutate(); }} loading={disconnectMutation.isPending}><Unplug className="h-4 w-4" />{t("instagramSettings.disconnect")}</Button> : null}
        <Link className="inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl border border-border-subtle bg-surface-2 px-4 text-sm font-black text-text-primary transition hover:bg-surface-hover" href="/settings/integrations/instagram">{t("instagramSettings.openSettings")}<ArrowRight className="h-4 w-4" /></Link>
        {connected && canOpenDirect ? <Link className="inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl bg-primary px-4 text-sm font-black text-primary-foreground transition hover:bg-primary-hover" href="/direct"><MessageCircle className="h-4 w-4" />{t("instagramSettings.openDirect")}</Link> : null}
      </div>
      {!canManage ? <p className="mt-4 rounded-2xl bg-surface-2 p-3 text-sm text-text-secondary">{t("instagramSettings.readOnly")}</p> : null}
    </Card>
  );
}

function ConnectedSummary({ data, permissionOk }: { data: InstagramConnectionStatusResponse; permissionOk: boolean }) {
  const { t } = useI18n();
  const rows = [
    [t("instagramSettings.username"), data.instagram_username ? `@${data.instagram_username}` : "—"],
    [t("instagramSettings.accountType"), data.instagram_account_type ?? "—"],
    [t("instagramSettings.tokenExpiry"), formatDate(data.token_expires_at)],
    [t("instagramSettings.messagingPermission"), permissionOk ? t("instagramSettings.permissionGranted") : t("instagramSettings.permissionMissing")],
    [t("instagramSettings.webhookStatus"), data.subscribed_webhook_fields.length ? data.subscribed_webhook_fields.join(", ") : "—"],
    [t("instagramSettings.lastWebhook"), formatDate(data.last_webhook_at)],
    [t("instagramSettings.lastInbound"), formatDate(data.last_message_received_at)],
    [t("instagramSettings.autoReplies"), t("instagramSettings.disabled")],
    [t("instagramSettings.outboundStatus"), t("instagramSettings.manualOutbound")],
  ];
  return <dl className="mt-5 grid gap-3 text-sm md:grid-cols-2">{rows.map(([label, value]) => <div key={label} className="rounded-2xl border border-border-subtle bg-surface-2 p-3"><dt className="text-xs font-black uppercase tracking-[0.12em] text-text-muted">{label}</dt><dd className="mt-1 font-bold text-text-primary">{value}</dd></div>)}</dl>;
}
