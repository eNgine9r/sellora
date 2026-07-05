"use client";

import Link from "next/link";
import { Bell, Plus, Settings, ShoppingBag, Users } from "lucide-react";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { FeedbackDialog } from "@/components/feedback-dialog";
import { LanguageSwitcher } from "@/components/language-switcher";
import { ThemeToggle } from "@/components/theme-toggle";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { useI18n } from "@/i18n/provider";
import { CurrentUser, WorkspaceMembership } from "@/types/auth";

function userName(user: CurrentUser | null) {
  const name = [user?.first_name, user?.last_name].filter(Boolean).join(" ").trim();
  return name || user?.email || "Sellora";
}

export function MobileMoreSheet({ open, currentUser, currentWorkspace, currentWorkspaceId, memberships, onClose, onLogout, onSwitchWorkspace, onWorkspaceCreated, onCreateOrder }: { open: boolean; currentUser: CurrentUser | null; currentWorkspace: WorkspaceMembership | null; currentWorkspaceId: string | null; memberships: WorkspaceMembership[]; onClose: () => void; onLogout: () => void; onSwitchWorkspace: (workspaceId: string) => void; onWorkspaceCreated: () => Promise<void>; onCreateOrder: () => void }) {
  const { t } = useI18n();

  return (
    <BottomSheet open={open} title={t("accountMenu.more")} closeLabel={t("actions.close")} onClose={onClose}>
      <div className="grid min-w-0 gap-4 mobile-more-sheet">
        <section className="rounded-3xl bg-slate-50 p-4 dark:bg-white/5" aria-label={t("accountMenu.user")}> 
          <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">{t("accountMenu.user")}</p>
          <p className="mt-2 truncate text-lg font-black text-slate-950 dark:text-white">{userName(currentUser)}</p>
          <p className="truncate text-sm text-slate-500 dark:text-slate-400">{currentUser?.email}</p>
          <p className="mt-2 truncate text-sm font-bold text-violet-700 dark:text-violet-200">{currentWorkspace?.workspace_name ?? t("accountMenu.currentWorkspace")}</p>
        </section>

        <WorkspaceSwitcher memberships={memberships} currentWorkspaceId={currentWorkspaceId} onSwitchWorkspace={onSwitchWorkspace} onCreated={onWorkspaceCreated} onClose={onClose} />

        <section className="grid gap-2" aria-label={t("accountMenu.quickActions")}>
          <p className="px-1 text-xs font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">{t("accountMenu.quickActions")}</p>
          <button className="flex min-h-11 items-center gap-3 rounded-2xl bg-violet-600 px-3 text-left text-sm font-black text-white" type="button" onClick={() => { onClose(); onCreateOrder(); }}>
            <ShoppingBag className="h-4 w-4" /> {t("topbar.createOrder")}
          </button>
          <FeedbackDialog workspaceId={currentWorkspaceId} onOpenChange={(nextOpen) => { if (nextOpen) onClose(); }} buttonClassName="min-h-11 w-full rounded-2xl border border-violet-200 bg-violet-50 px-3 text-left text-sm font-black text-violet-700 dark:border-violet-400/30 dark:bg-violet-400/10 dark:text-violet-100" />
          <button className="flex min-h-11 items-center gap-3 rounded-2xl border border-slate-200 px-3 text-left text-sm font-bold text-slate-700 dark:border-white/10 dark:text-slate-100" type="button">
            <Bell className="h-4 w-4" /> {t("topbar.notifications")}
          </button>
        </section>

        <section className="grid gap-2" aria-label={t("accountMenu.settings")}>
          <p className="px-1 text-xs font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">{t("accountMenu.settings")}</p>
          <Link className="flex min-h-11 items-center gap-3 rounded-2xl border border-slate-200 px-3 text-sm font-bold text-slate-700 dark:border-white/10 dark:text-slate-100" href="/settings/workspace" onClick={onClose}>
            <Settings className="h-4 w-4" /> {t("accountMenu.workspace")}
          </Link>
          <Link className="flex min-h-11 items-center gap-3 rounded-2xl border border-slate-200 px-3 text-sm font-bold text-slate-700 dark:border-white/10 dark:text-slate-100" href="/settings/team" onClick={onClose}>
            <Users className="h-4 w-4" /> {t("accountMenu.team")}
          </Link>
          <div className="grid grid-cols-2 gap-2">
            <LanguageSwitcher compact />
            <ThemeToggle compact />
          </div>
        </section>

        <button className="flex min-h-11 items-center justify-center gap-2 rounded-2xl border border-red-100 bg-red-50 px-3 text-sm font-black text-red-700 dark:border-red-400/20 dark:bg-red-500/10 dark:text-red-200" type="button" onClick={() => { onClose(); onLogout(); }}>
          <Plus className="h-4 w-4 rotate-45" /> {t("actions.logout")}
        </button>
      </div>
    </BottomSheet>
  );
}
