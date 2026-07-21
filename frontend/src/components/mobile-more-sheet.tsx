"use client";

import Link from "next/link";
import { LogOut, MessageCircle, Settings, ShoppingBag, Users } from "lucide-react";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { FeedbackDialog } from "@/components/feedback-dialog";
import { LanguageSwitcher } from "@/components/language-switcher";
import { ThemeToggle } from "@/components/theme-toggle";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { useI18n } from "@/i18n/provider";
import { CurrentUser, WorkspaceMembership } from "@/types/auth";

const actionClass = "flex min-h-11 w-full min-w-0 items-center gap-3 rounded-2xl border border-border-subtle bg-surface-2 px-3 text-left text-sm font-bold text-text-primary transition hover:border-border-strong hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring";

function userName(user: CurrentUser | null) {
  const name = [user?.first_name, user?.last_name].filter(Boolean).join(" ").trim();
  return name || user?.email || "Sellora";
}

export function MobileMoreSheet({ open, currentUser, currentWorkspace, currentWorkspaceId, memberships, onClose, onLogout, onSwitchWorkspace, onWorkspaceCreated, onCreateOrder }: { open: boolean; currentUser: CurrentUser | null; currentWorkspace: WorkspaceMembership | null; currentWorkspaceId: string | null; memberships: WorkspaceMembership[]; onClose: () => void; onLogout: () => void; onSwitchWorkspace: (workspaceId: string) => void; onWorkspaceCreated: () => Promise<void>; onCreateOrder: () => void }) {
  const { t } = useI18n();

  return (
    <BottomSheet open={open} title={t("accountMenu.more")} closeLabel={t("actions.close")} onClose={onClose}>
      <div className="mobile-more-sheet grid min-w-0 gap-4">
        <section className="rounded-3xl border border-border-subtle bg-surface-2 p-4" aria-label={t("accountMenu.user")}>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-text-muted">{t("accountMenu.user")}</p>
          <p className="mt-2 truncate text-lg font-black text-text-primary">{userName(currentUser)}</p>
          <p className="truncate text-sm text-text-muted">{currentUser?.email}</p>
          <p className="mt-2 truncate text-sm font-bold text-primary">{currentWorkspace?.workspace_name ?? t("accountMenu.currentWorkspace")}</p>
        </section>

        <WorkspaceSwitcher memberships={memberships} currentWorkspaceId={currentWorkspaceId} onSwitchWorkspace={onSwitchWorkspace} onCreated={onWorkspaceCreated} onClose={onClose} />

        <section className="grid gap-2" aria-label={t("accountMenu.quickActions")}>
          <p className="px-1 text-xs font-black uppercase tracking-[0.18em] text-text-muted">{t("accountMenu.quickActions")}</p>
          <button className="flex min-h-11 w-full items-center gap-3 rounded-2xl bg-primary px-3 text-left text-sm font-black text-primary-foreground shadow-[var(--shadow-control)] transition hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" type="button" onClick={() => { onClose(); onCreateOrder(); }}>
            <ShoppingBag className="h-4 w-4" /> {t("topbar.createOrder")}
          </button>
          <Link className={actionClass} href="/direct" onClick={onClose}>
            <MessageCircle className="h-4 w-4" /> {t("navigation.direct")}
          </Link>
          <FeedbackDialog workspaceId={currentWorkspaceId} onOpenChange={(nextOpen) => { if (nextOpen) onClose(); }} buttonClassName={actionClass} />
        </section>

        <section className="grid gap-2" aria-label={t("accountMenu.settings")}>
          <p className="px-1 text-xs font-black uppercase tracking-[0.18em] text-text-muted">{t("accountMenu.settings")}</p>
          <Link className={actionClass} href="/settings/workspace" onClick={onClose}>
            <Settings className="h-4 w-4" /> {t("accountMenu.workspace")}
          </Link>
          <Link className={actionClass} href="/settings/team" onClick={onClose}>
            <Users className="h-4 w-4" /> {t("accountMenu.team")}
          </Link>
          <div className="grid grid-cols-2 gap-2">
            <LanguageSwitcher compact />
            <ThemeToggle compact />
          </div>
        </section>

        <button className="flex min-h-11 w-full items-center justify-center gap-2 rounded-2xl border border-danger/25 bg-[var(--danger-surface)] px-3 text-sm font-black text-[var(--danger-foreground)] transition hover:brightness-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-danger" type="button" onClick={() => { onClose(); onLogout(); }}>
          <LogOut className="h-4 w-4" /> {t("actions.logout")}
        </button>
      </div>
    </BottomSheet>
  );
}
