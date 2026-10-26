"use client";

import Link from "next/link";
import { LogOut, MessageCircle, Settings, Users } from "lucide-react";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { FeedbackDialog } from "@/components/feedback-dialog";
import { LanguageSwitcher } from "@/components/language-switcher";
import { ThemeToggle } from "@/components/theme-toggle";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { useI18n } from "@/i18n/provider";
import { CurrentUser, WorkspaceMembership } from "@/types/auth";

const actionClass = "flex min-h-11 w-full min-w-0 items-center gap-3 rounded-xl px-3 text-left text-sm font-medium text-text-primary transition hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring";

function userName(user: CurrentUser | null) {
  const name = [user?.first_name, user?.last_name].filter(Boolean).join(" ").trim();
  return name || user?.email || "Sellora";
}

export function MobileMoreSheet({ open, currentUser, currentWorkspace, currentWorkspaceId, memberships, onClose, onLogout, onSwitchWorkspace, onWorkspaceCreated }: { open: boolean; currentUser: CurrentUser | null; currentWorkspace: WorkspaceMembership | null; currentWorkspaceId: string | null; memberships: WorkspaceMembership[]; onClose: () => void; onLogout: () => void; onSwitchWorkspace: (workspaceId: string) => void; onWorkspaceCreated: () => Promise<void> }) {
  const { t } = useI18n();
  const initial = userName(currentUser).slice(0, 1).toUpperCase();

  return (
    <BottomSheet open={open} title={t("accountMenu.profile")} closeLabel={t("actions.close")} onClose={onClose}>
      <div className="mobile-more-sheet grid min-w-0 gap-3 pb-1">
        <section className="flex min-w-0 items-center gap-3 rounded-2xl border border-border-subtle bg-surface-2 p-3" aria-label={t("accountMenu.user")}>
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-primary/15 text-base font-semibold text-primary" aria-hidden="true">{initial}</span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-base font-semibold text-text-primary">{userName(currentUser)}</p>
            <p className="truncate text-xs text-text-muted">{currentUser?.email}</p>
          </div>
        </section>

        <WorkspaceSwitcher memberships={memberships} currentWorkspaceId={currentWorkspaceId} onSwitchWorkspace={onSwitchWorkspace} onCreated={onWorkspaceCreated} onClose={onClose} />

        <div className="h-px bg-border-subtle" aria-hidden="true" />

        <nav className="grid gap-0.5" aria-label={t("accountMenu.settings")}>
          <Link href="/settings/workspace" className={actionClass} onClick={onClose}><Settings className="h-[18px] w-[18px] text-text-secondary" aria-hidden="true" />{t("accountMenu.settings")}</Link>
          {currentWorkspace?.role === "OWNER" ? (
            <Link href="/settings/team" className={actionClass} onClick={onClose}><Users className="h-[18px] w-[18px] text-text-secondary" aria-hidden="true" />{t("accountMenu.team")}</Link>
          ) : null}
          <Link href="/direct" className={actionClass} onClick={onClose}><MessageCircle className="h-[18px] w-[18px] text-text-secondary" aria-hidden="true" />{t("navigation.direct")}</Link>
          <FeedbackDialog workspaceId={currentWorkspaceId} buttonClassName={actionClass} onOpenChange={(nextOpen) => { if (nextOpen) onClose(); }} />
        </nav>

        <div className="flex items-center justify-between gap-3 rounded-xl border border-border-subtle bg-surface-2 px-3 py-2">
          <span className="text-xs font-medium text-text-muted">{t("accountMenu.preferences")}</span>
          <div className="flex items-center gap-2"><LanguageSwitcher compact /><ThemeToggle compact /></div>
        </div>

        <button className="flex min-h-11 items-center gap-3 rounded-xl px-3 text-left text-sm font-medium text-danger transition hover:bg-[var(--danger-surface)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-danger" type="button" onClick={() => { onClose(); onLogout(); }}>
          <LogOut className="h-[18px] w-[18px]" aria-hidden="true" /> {t("actions.logout")}
        </button>
      </div>
    </BottomSheet>
  );
}
