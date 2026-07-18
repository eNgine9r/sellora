"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Building2, Languages, PlugZap, ShieldCheck, UploadCloud, Users, Wand2 } from "lucide-react";
import { WorkspacePage, WorkspaceHeader, CompactSummary } from "@/components/crm-workspace";
import { Card, StatusBadge } from "@/components/ui/primitives";
import { LanguageSwitcher } from "@/components/language-switcher";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { fetchInstagramStatus } from "@/services/meta-instagram";

export default function SettingsOverviewPage() {
  const { t } = useI18n();
  const { currentWorkspace, currentWorkspaceId, status } = useAuth();
  const role = currentWorkspace?.role ?? "ANALYST";
  const workspaceId = currentWorkspaceId ?? "";
  const instagramStatus = useQuery({ queryKey: ["instagram-connection-status", workspaceId], queryFn: fetchInstagramStatus, enabled: status === "authenticated" && Boolean(workspaceId) });
  const integrationsSummary = instagramStatus.data?.status === "CONNECTED" ? t("settings.status.instagramConnected") : t("settings.status.integrationCount", { connected: 0, total: 3 });
  const settingsRoutes = [
    { href: "/settings/workspace", icon: Building2, titleKey: "settings.cards.workspaceTitle", descriptionKey: "settings.cards.workspaceDescription", statusKey: "settings.status.configured", tone: "success" as const },
    { href: "/settings/team", icon: Users, titleKey: "settings.cards.teamTitle", descriptionKey: "settings.cards.teamDescription", statusKey: "settings.status.roles", tone: "info" as const },
    { href: "/settings/import", icon: UploadCloud, titleKey: "settings.cards.importTitle", descriptionKey: "settings.cards.importDescription", statusKey: "settings.status.available", tone: "success" as const },
    { href: "/settings/integrations", icon: PlugZap, titleKey: "settings.cards.integrationsTitle", descriptionKey: "settings.cards.integrationsDescription", statusKey: instagramStatus.data?.status === "CONNECTED" ? "settings.status.instagramConnected" : "settings.status.requiresSetup", tone: instagramStatus.data?.status === "CONNECTED" ? "success" as const : "warning" as const },
    { href: "/settings/feedback", icon: Wand2, titleKey: "settings.cards.feedbackTitle", descriptionKey: "settings.cards.feedbackDescription", statusKey: "settings.status.ownerManaged", tone: "neutral" as const },
  ];

  return (
    <WorkspacePage>
      <WorkspaceHeader
        eyebrow={t("settings.label")}
        title={t("settings.title")}
        description={t("settings.subtitle")}
        actions={<StatusBadge tone="info">{t(`roles.${role}`)}</StatusBadge>}
      />
      <CompactSummary items={[
        { label: t("settings.summary.workspace"), value: currentWorkspace?.workspace_name ?? "—", helper: t("settings.summary.workspaceHelp") },
        { label: t("settings.summary.role"), value: t(`roles.${role}`), helper: t("settings.summary.roleHelp") },
        { label: t("settings.summary.imports"), value: t("settings.status.available"), helper: t("settings.summary.importsHelp") },
        { label: t("settings.summary.integrations"), value: integrationsSummary, helper: t("settings.summary.integrationsHelp") },
      ]} />

      <section className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="grid min-w-0 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {settingsRoutes.map((item) => {
            const Icon = item.icon;
            return (
              <Link key={item.href} href={item.href} className="group min-w-0 rounded-[var(--radius-card)] border border-border-subtle bg-surface-1 p-5 shadow-[var(--shadow-card)] transition hover:-translate-y-0.5 hover:border-primary/40 hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring motion-reduce:transition-none">
                <div className="flex items-start justify-between gap-3">
                  <span className="grid h-11 w-11 place-items-center rounded-2xl bg-surface-selected text-primary"><Icon className="h-5 w-5" /></span>
                  <StatusBadge tone={item.tone}>{t(item.statusKey)}</StatusBadge>
                </div>
                <h2 className="mt-4 text-lg font-black text-text-primary">{t(item.titleKey)}</h2>
                <p className="mt-2 text-sm leading-6 text-text-secondary">{t(item.descriptionKey)}</p>
                <span className="mt-5 inline-flex items-center gap-2 text-sm font-black text-primary">{t("actions.open")}<ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" /></span>
              </Link>
            );
          })}
        </div>
        <Card className="grid gap-4 self-start">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.16em] text-text-muted">{t("settings.preferences.title")}</p>
            <h2 className="mt-2 text-xl font-black text-text-primary">{t("settings.preferences.heading")}</h2>
            <p className="mt-2 text-sm leading-6 text-text-secondary">{t("settings.preferences.description")}</p>
          </div>
          <div className="grid gap-3 rounded-3xl border border-border-subtle bg-surface-2 p-4">
            <div className="flex items-center justify-between gap-3"><span className="inline-flex items-center gap-2 text-sm font-bold text-text-primary"><Languages className="h-4 w-4" />{t("language.label")}</span><LanguageSwitcher /></div>
            <div className="flex items-center justify-between gap-3"><span className="inline-flex items-center gap-2 text-sm font-bold text-text-primary"><ShieldCheck className="h-4 w-4" />{t("settings.preferences.appearance")}</span><ThemeToggle /></div>
          </div>
          <div className="rounded-3xl border border-warning/25 bg-[var(--warning-surface)] p-4 text-sm leading-6 text-[var(--warning-foreground)]">
            <p className="font-black">{t("settings.attention.title")}</p>
            <p>{t("settings.attention.description")}</p>
          </div>
        </Card>
      </section>
    </WorkspacePage>
  );
}
