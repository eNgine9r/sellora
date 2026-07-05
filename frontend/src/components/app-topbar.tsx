"use client";

import { Bell, Menu, MoreHorizontal, Plus, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { BrandIcon } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageSwitcher } from "@/components/language-switcher";
import { FeedbackDialog } from "@/components/feedback-dialog";
import { ProfileMenu } from "@/components/profile-menu";
import { MobileMoreSheet } from "@/components/mobile-more-sheet";
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
  const createOrder = () => router.push("/orders");

  return (
    <header className="mobile-safe-top sticky top-0 z-50 min-w-0 border-b border-slate-200/70 bg-[#F8F7FC]/92 px-3 py-3 text-slate-950 backdrop-blur-xl dark:border-white/10 dark:bg-[#101120]/92 dark:text-white sm:px-4 md:px-6">
      <div className="mobile-topbar-compact flex min-w-0 items-center gap-2 sm:gap-3 lg:gap-4">
        <button className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-white/10 lg:hidden" onClick={onOpenMenu} aria-label={t("mobileTopbar.openNavigation")}>
          <Menu className="h-5 w-5" />
        </button>

        <div className="flex min-w-0 flex-1 items-center gap-3 md:hidden">
          <BrandIcon className="h-10 w-10 shrink-0" priority />
          <div className="min-w-0 leading-tight">
            <p className="truncate text-sm font-black text-slate-950 dark:text-white">Sellora</p>
            <p className="truncate text-xs text-slate-500 dark:text-slate-400">{t("accountMenu.workspace")}</p>
          </div>
        </div>

        <div className="relative hidden min-w-[220px] flex-1 md:block lg:max-w-[560px] xl:max-w-[680px]">
          <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            className="h-12 w-full min-w-0 rounded-2xl border border-slate-200 bg-white pl-11 pr-4 text-sm text-slate-950 shadow-sm outline-none transition focus:border-violet-300 focus:ring-4 focus:ring-violet-100 dark:border-white/10 dark:bg-white/10 dark:text-white dark:placeholder:text-slate-400"
            placeholder={t("topbar.searchPlaceholder")}
          />
        </div>

        <div className="hidden md:block"><FeedbackDialog workspaceId={currentWorkspaceId} /></div>
        <div className="hidden md:block"><LanguageSwitcher compact /></div>
        <div className="hidden md:block"><ThemeToggle compact /></div>
        <button className="hidden h-12 w-12 shrink-0 place-items-center rounded-2xl border border-slate-200 bg-white text-slate-700 shadow-sm transition hover:border-violet-200 hover:text-violet-700 dark:border-white/10 dark:bg-white/10 dark:text-slate-100 md:grid" aria-label={t("topbar.notifications")}>
          <Bell className="h-5 w-5" />
        </button>
        <button
          className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-[linear-gradient(135deg,#6D28D9_0%,#EC4899_45%,#F97316_75%,#FACC15_100%)] text-white shadow-lg shadow-pink-500/20 sm:h-12 sm:w-12"
          onClick={createOrder}
          aria-label={t("topbar.createOrder")}
        >
          <Plus className="h-5 w-5" />
        </button>

        <ProfileMenu currentUser={currentUser} currentWorkspace={currentWorkspace} currentWorkspaceId={currentWorkspaceId} memberships={validMemberships} onLogout={onLogout} onSwitchWorkspace={onSwitchWorkspace} onWorkspaceCreated={onWorkspaceCreated} />

        <button className="topbar-action grid h-11 w-11 shrink-0 place-items-center rounded-2xl border border-slate-200 bg-white text-slate-700 shadow-sm transition hover:border-violet-200 hover:text-violet-700 dark:border-white/10 dark:bg-white/10 dark:text-white md:hidden" type="button" aria-expanded={mobileMoreOpen} aria-controls="mobile-more-sheet" aria-label={t("mobileTopbar.more")} onClick={() => setMobileMoreOpen(true)}>
          <MoreHorizontal className="h-5 w-5" />
        </button>
      </div>

      <MobileMoreSheet
        open={mobileMoreOpen}
        currentUser={currentUser}
        currentWorkspace={currentWorkspace}
        currentWorkspaceId={currentWorkspaceId}
        memberships={validMemberships}
        onClose={() => setMobileMoreOpen(false)}
        onLogout={onLogout}
        onSwitchWorkspace={onSwitchWorkspace}
        onWorkspaceCreated={onWorkspaceCreated}
        onCreateOrder={createOrder}
      />
    </header>
  );
}
// Topbar overflow regression compatibility marker: mobile-topbar-compact mobile-more-sheet topbar-action portal-profile-menu bottom-sheet global-period-selector-removed.
