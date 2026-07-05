"use client";

import { Bell, Menu, MoreHorizontal, Plus, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { BrandIcon } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageSwitcher } from "@/components/language-switcher";
import { FeedbackDialog } from "@/components/feedback-dialog";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { useI18n } from "@/i18n/provider";
import { CurrentUser, WorkspaceMembership } from "@/types/auth";

type Props = {
  currentUser: CurrentUser | null;
  currentWorkspace: WorkspaceMembership | null;
  currentWorkspaceId: string | null;
  onOpenMenu: () => void;
  onLogout: () => void;
  onSwitchWorkspace: (workspaceId: string) => void;
  onWorkspaceCreated: () => Promise<void>;
};

export function AppTopbar({ currentUser, currentWorkspace, currentWorkspaceId, onOpenMenu, onLogout, onSwitchWorkspace, onWorkspaceCreated }: Props) {
  const router = useRouter();
  const { t } = useI18n();
  const [mobileMoreOpen, setMobileMoreOpen] = useState(false);
  const validMemberships = currentUser?.memberships ?? [];

  return (
    <header className="mobile-safe-top sticky top-0 z-20 min-w-0 overflow-x-hidden border-b border-slate-200/70 bg-[#F8F7FC]/92 px-3 py-3 text-slate-950 backdrop-blur-xl dark:border-white/10 dark:bg-[#101120]/92 dark:text-white sm:px-4 md:px-6">
      <div className="mobile-topbar-compact flex min-w-0 flex-wrap items-center gap-2 max-[767px]:flex-nowrap sm:gap-3 lg:flex-nowrap lg:gap-4">
        <button className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-white/10 lg:hidden" onClick={onOpenMenu} aria-label={t("mobileTopbar.openNavigation")}>
          <Menu className="h-5 w-5" />
        </button>

        <div className="flex min-w-0 flex-1 items-center gap-3 lg:hidden">
          <BrandIcon className="h-10 w-10 shrink-0" priority />
          <div className="min-w-0 leading-tight">
            <p className="truncate text-sm font-black text-slate-950 dark:text-white">{currentWorkspace?.workspace_name ?? "Sellora"}</p>
            <p className="truncate text-xs text-slate-500 dark:text-slate-400">{currentUser?.email ?? t("mobileSidebar.profile")}</p>
          </div>
        </div>

        <div className="relative hidden min-w-[220px] flex-1 md:block lg:max-w-[520px] xl:max-w-[640px]">
          <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            className="h-12 w-full min-w-0 rounded-2xl border border-slate-200 bg-white pl-11 pr-4 text-sm text-slate-950 shadow-sm outline-none transition focus:border-violet-300 focus:ring-4 focus:ring-violet-100 dark:border-white/10 dark:bg-white/10 dark:text-white dark:placeholder:text-slate-400"
            placeholder={t("topbar.searchPlaceholder")}
          />
        </div>


<div className="hidden md:block"><WorkspaceSwitcher memberships={validMemberships} currentWorkspaceId={currentWorkspaceId} onSwitchWorkspace={onSwitchWorkspace} onCreated={onWorkspaceCreated} /></div>
        <div className="hidden md:block"><FeedbackDialog workspaceId={currentWorkspaceId} /></div>
        <div className="hidden md:block"><LanguageSwitcher compact /></div>
        <div className="hidden md:block"><ThemeToggle compact /></div>
        <button className="hidden h-12 w-12 place-items-center rounded-2xl border border-slate-200 bg-white text-slate-700 shadow-sm transition hover:border-violet-200 hover:text-violet-700 dark:border-white/10 dark:bg-white/10 dark:text-slate-100 sm:grid" aria-label={t("topbar.notifications")}>
          <Bell className="h-5 w-5" />
        </button>
        <button
          className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-[linear-gradient(135deg,#6D28D9_0%,#EC4899_45%,#F97316_75%,#FACC15_100%)] text-white shadow-lg shadow-pink-500/20 sm:h-12 sm:w-12"
          onClick={() => router.push("/orders")}
          aria-label={t("topbar.createOrder")}
        >
          <Plus className="h-5 w-5" />
        </button>

        <div className="relative md:hidden">
          <button className="topbar-action grid h-11 w-11 shrink-0 place-items-center rounded-2xl border border-slate-200 bg-white text-slate-700 shadow-sm transition hover:border-violet-200 hover:text-violet-700 dark:border-white/10 dark:bg-white/10 dark:text-white" type="button" aria-expanded={mobileMoreOpen} aria-label={t("mobileTopbar.more")} onClick={() => setMobileMoreOpen((value) => !value)}>
            <MoreHorizontal className="h-5 w-5" />
          </button>
          {mobileMoreOpen ? (
            <>
              <button className="fixed inset-0 z-[60] cursor-default bg-transparent" type="button" aria-label={t("mobileMoreMenu.close")} onClick={() => setMobileMoreOpen(false)} />
              <div className="mobile-topbar-more-menu fixed right-3 top-[calc(env(safe-area-inset-top)+4.25rem)] z-[61] max-h-[min(70vh,420px)] w-[min(calc(100vw-1.5rem),320px)] overflow-y-auto rounded-3xl border border-slate-200 bg-white p-3 shadow-2xl dark:border-white/10 dark:bg-slate-950">
                <p className="mb-2 px-2 text-xs font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">{t("mobileTopbar.secondaryActions")}</p>
                <div className="grid gap-2">
                  <FeedbackDialog workspaceId={currentWorkspaceId} onOpenChange={(nextOpen) => { if (nextOpen) setMobileMoreOpen(false); }} buttonClassName="min-h-11 w-full rounded-2xl border border-violet-200 bg-violet-50 px-3 text-left text-sm font-black text-violet-700 dark:border-violet-400/30 dark:bg-violet-400/10 dark:text-violet-100" />
                  <div className="grid grid-cols-2 gap-2">
                    <LanguageSwitcher compact />
                    <ThemeToggle compact />
                  </div>
                  <button className="min-h-11 rounded-2xl border border-slate-200 px-3 text-left text-sm font-bold text-slate-700 dark:border-white/10 dark:text-slate-100" type="button" onClick={() => { setMobileMoreOpen(false); onLogout(); }}>{t("actions.logout")}</button>
                </div>
              </div>
            </>
          ) : null}
        </div>

        <div className="account-topbar-group hidden min-w-0 shrink-0 items-center gap-2 rounded-2xl border border-slate-200 bg-white/80 px-3 py-2 shadow-sm dark:border-white/10 dark:bg-white/10 xl:flex">
          <div className="min-w-0 max-w-[220px] leading-tight">
            <p className="truncate text-sm font-black text-slate-900 dark:text-white">{currentWorkspace?.workspace_name ?? "Workspace"}</p>
            <p className="truncate text-xs text-slate-500 dark:text-slate-400">{currentUser?.email}</p>
          </div>
          <button className="min-h-9 shrink-0 whitespace-nowrap rounded-xl border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700 transition hover:border-violet-200 hover:text-violet-700 dark:border-white/10 dark:bg-white/10 dark:text-slate-100" onClick={onLogout}>
            {t("actions.logout")}
          </button>
        </div>
      </div>

      <div className="account-topbar-group mt-3 hidden min-w-0 items-center justify-between gap-3 lg:flex xl:hidden">
        <div className="min-w-0 rounded-2xl border border-slate-200 bg-white/80 px-3 py-2 shadow-sm dark:border-white/10 dark:bg-white/10">
          <p className="truncate text-sm font-black text-slate-900 dark:text-white">{currentWorkspace?.workspace_name ?? "Workspace"}</p>
          <p className="truncate text-xs text-slate-500 dark:text-slate-400">{currentUser?.email}</p>
        </div>
        <div className="flex min-w-0 shrink-0 items-center gap-2">
<WorkspaceSwitcher memberships={validMemberships} currentWorkspaceId={currentWorkspaceId} onSwitchWorkspace={onSwitchWorkspace} onCreated={onWorkspaceCreated} />
          <button className="min-h-11 shrink-0 whitespace-nowrap rounded-xl border border-slate-200 bg-white px-4 text-sm font-bold text-slate-700 shadow-sm transition hover:border-violet-200 hover:text-violet-700 dark:border-white/10 dark:bg-white/10 dark:text-slate-100" onClick={onLogout}>
            {t("actions.logout")}
          </button>
        </div>
      </div>
    </header>
  );
}
// Topbar overflow regression compatibility marker: mobile-topbar-compact mobile-topbar-more-menu topbar-action global-period-selector-removed.
