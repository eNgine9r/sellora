"use client";

import { Bell, Menu, MoreHorizontal, Plus, Search, ShoppingBag } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { BrandIcon } from "@/components/brand";
import { DirectLiveEvent } from "@/types/direct";
import { useDirectLive } from "@/components/direct-live-provider";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageSwitcher } from "@/components/language-switcher";
import { FeedbackDialog } from "@/components/feedback-dialog";
import { ProfileMenu } from "@/components/profile-menu";
import { MobileMoreSheet } from "@/components/mobile-more-sheet";
import { IconButton } from "@/components/ui/primitives";
import { useI18n } from "@/i18n/provider";
import { CurrentUser, WorkspaceMembership } from "@/types/auth";

type Props = {
  currentUser: CurrentUser | null;
  currentWorkspace: WorkspaceMembership | null;
  currentWorkspaceId: string | null;
  mobileMoreOpen: boolean;
  onOpenMenu: () => void;
  onOpenMobileMore: () => void;
  onCloseMobileMore: () => void;
  onLogout: () => void;
  onSwitchWorkspace: (workspaceId: string) => void;
  onWorkspaceCreated: () => Promise<void>;
};

function participantLabel(event: DirectLiveEvent) {
  return event.participant_display_name
    ?? (event.participant_username ? `@${event.participant_username}` : null)
    ?? "Клієнт Instagram";
}

export function AppTopbar({ currentUser, currentWorkspace, currentWorkspaceId, mobileMoreOpen, onOpenMenu, onOpenMobileMore, onCloseMobileMore, onLogout, onSwitchWorkspace, onWorkspaceCreated }: Props) {
  const router = useRouter();
  const { t } = useI18n();
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const validMemberships = currentUser?.memberships ?? [];
  const createOrder = () => router.push("/orders");
  const { summary, isLive, isError, permission, requestBrowserNotifications, openConversation } = useDirectLive();
  const unreadTotal = summary?.unread_total ?? 0;

  const openNotification = (event: DirectLiveEvent) => {
    setNotificationsOpen(false);
    openConversation(event.conversation_id);
  };

  return (
    <header className="mobile-safe-top sticky top-0 z-50 min-w-0 border-b border-border-subtle bg-canvas/92 px-3 py-3 text-text-primary backdrop-blur-xl sm:px-4 md:px-6 lg:static lg:h-[var(--topbar-height)] lg:bg-canvas/92 lg:py-0" data-shell-topbar>
      <div className="mobile-topbar-compact flex w-full min-w-0 items-center gap-2 sm:gap-3 lg:h-full lg:gap-4">
        <IconButton className="lg:hidden" onClick={onOpenMenu} aria-label={t("mobileTopbar.openNavigation")}>
          <Menu className="h-5 w-5" />
        </IconButton>

        <div className="flex min-w-0 flex-1 items-center gap-3 md:hidden">
          <BrandIcon className="h-10 w-10 shrink-0" priority />
          <div className="min-w-0 leading-tight">
            <p className="truncate text-sm font-black text-text-primary">Sellora</p>
            <p className="truncate text-xs text-text-muted">{currentWorkspace?.workspace_name ?? t("accountMenu.workspace")}</p>
          </div>
        </div>

        <div className="relative hidden min-w-[220px] flex-1 md:block">
          <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <input className="h-11 w-full min-w-0 rounded-2xl border border-border-subtle bg-surface-2 pl-11 pr-4 text-sm font-semibold text-text-primary shadow-sm outline-none transition placeholder:text-text-muted hover:border-border-strong focus:border-focus-ring focus:ring-2 focus:ring-focus-ring/30" placeholder={t("topbar.searchPlaceholder")} />
        </div>

        <div className="hidden md:block"><FeedbackDialog workspaceId={currentWorkspaceId} /></div>
        <div className="hidden md:block"><LanguageSwitcher compact /></div>
        <div className="hidden md:block"><ThemeToggle compact /></div>
        <div className="relative hidden md:block">
          <IconButton aria-label={t("topbar.notifications")} aria-expanded={notificationsOpen} onClick={() => setNotificationsOpen((value) => !value)} data-direct-notification-bell>
            <Bell className="h-5 w-5" />
            {unreadTotal > 0 ? <span className="absolute -right-1.5 -top-1.5 grid min-h-5 min-w-5 place-items-center rounded-full bg-rose-500 px-1 text-[0.65rem] font-black text-white">{unreadTotal > 99 ? "99+" : unreadTotal}</span> : null}
          </IconButton>
          {notificationsOpen ? (
            <div className="absolute right-0 top-12 z-[70] w-[min(92vw,420px)] overflow-hidden rounded-3xl border border-border-subtle bg-surface-1 shadow-2xl" data-direct-notification-center>
              <div className="flex items-start justify-between gap-3 border-b border-border-subtle p-4">
                <div><p className="font-black">Сповіщення Direct</p><p className={`mt-1 text-xs font-semibold ${isError ? "text-rose-600" : isLive ? "text-emerald-600" : "text-amber-600"}`}>{isError ? "Live-зʼєднання тимчасово недоступне" : isLive ? "Live-оновлення активні" : "Підключення до live-оновлень…"}</p></div>
                {summary?.order_intent_count ? <span className="rounded-full bg-amber-500/15 px-2 py-1 text-xs font-black text-amber-700">Замовлення: {summary.order_intent_count}</span> : null}
              </div>
              {permission === "default" ? <div className="border-b border-border-subtle p-3"><button type="button" onClick={() => void requestBrowserNotifications()} className="min-h-11 w-full rounded-2xl bg-primary/15 px-3 text-sm font-black text-primary hover:bg-primary/20">Увімкнути системні сповіщення</button></div> : null}
              <div className="max-h-[420px] overflow-y-auto p-2">
                {(summary?.events ?? []).length === 0 ? <p className="p-4 text-center text-sm text-text-muted">Нових непрочитаних повідомлень немає.</p> : (summary?.events ?? []).slice(0, 10).map((event) => (
                  <button key={event.message_id} type="button" onClick={() => openNotification(event)} className="flex min-h-11 w-full items-start gap-3 rounded-2xl p-3 text-left transition hover:bg-surface-hover">
                    <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-2xl ${event.order_intent ? "bg-amber-500/15 text-amber-600" : "bg-primary/15 text-primary"}`}>{event.order_intent ? <ShoppingBag className="h-4 w-4" /> : <Bell className="h-4 w-4" />}</span>
                    <span className="min-w-0 flex-1"><span className="flex items-center justify-between gap-2"><span className="truncate text-sm font-black">{participantLabel(event)}</span>{event.order_intent ? <span className="shrink-0 rounded-full bg-amber-500/15 px-2 py-0.5 text-[0.65rem] font-black text-amber-700">Ймовірне замовлення</span> : null}</span><span className="mt-1 block line-clamp-2 text-xs text-text-muted">{event.text_preview}</span></span>
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        <IconButton variant="brand" onClick={createOrder} aria-label={t("topbar.createOrder")}><Plus className="h-5 w-5" /></IconButton>
        <ProfileMenu currentUser={currentUser} currentWorkspace={currentWorkspace} currentWorkspaceId={currentWorkspaceId} memberships={validMemberships} onLogout={onLogout} onSwitchWorkspace={onSwitchWorkspace} onWorkspaceCreated={onWorkspaceCreated} />
        <IconButton className="topbar-action md:hidden" type="button" aria-expanded={mobileMoreOpen} aria-controls="mobile-more-sheet" aria-label={t("mobileTopbar.more")} onClick={onOpenMobileMore}>
          <MoreHorizontal className="h-5 w-5" />
        </IconButton>
      </div>

      <MobileMoreSheet open={mobileMoreOpen} currentUser={currentUser} currentWorkspace={currentWorkspace} currentWorkspaceId={currentWorkspaceId} memberships={validMemberships} onClose={onCloseMobileMore} onLogout={onLogout} onSwitchWorkspace={onSwitchWorkspace} onWorkspaceCreated={onWorkspaceCreated} onCreateOrder={createOrder} />
    </header>
  );
}

// Mobile UI contract: controlled-more-sheet shared-icon-buttons minimum-touch-target-44.
