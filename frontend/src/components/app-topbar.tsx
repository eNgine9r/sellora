"use client";

import { Bell, Menu, MessageSquare, Plus, ShoppingBag } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getSmartSaleCandidates } from "@/services/smart-sale";
import { BrandIcon } from "@/components/brand";
import { DirectLiveEvent } from "@/types/direct";
import { useDirectLive } from "@/components/direct-live-provider";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageSwitcher } from "@/components/language-switcher";
import { GlobalSearch } from "@/components/global-search";
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

export function AppTopbar({ currentUser, currentWorkspace, currentWorkspaceId, mobileMoreOpen, onOpenMenu, onCloseMobileMore, onLogout, onSwitchWorkspace, onWorkspaceCreated }: Props) {
  const router = useRouter();
  const { t } = useI18n();
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const notificationRef = useRef<HTMLDivElement>(null);
  const validMemberships = currentUser?.memberships ?? [];
  const createOrder = () => router.push("/orders?create=1");
  const { summary, isLive, isError, permission, requestBrowserNotifications, openConversation } = useDirectLive();
  const unreadTotal = summary?.unread_total ?? 0;
  const canReviewSales = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";
  const canCreateOrder = canReviewSales;
  const sales = useQuery({
    queryKey: ["smart-sale-candidates", currentWorkspaceId],
    queryFn: () => getSmartSaleCandidates(currentWorkspaceId!),
    enabled: canReviewSales && Boolean(currentWorkspaceId),
    refetchInterval: 90_000,
    staleTime: 90_000,
    retry: 1,
  });
  const saleCandidates = (sales.data ?? []).filter(item => !!item.conversation_id && item.state !== "CONFIRMED");
  const bellCount = unreadTotal + saleCandidates.length;

  useEffect(() => {
    if (!notificationsOpen) return;
    const onOutside = (event: PointerEvent) => {
      if (!notificationRef.current?.contains(event.target as Node)) setNotificationsOpen(false);
    };
    const onEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setNotificationsOpen(false);
    };
    document.addEventListener("pointerdown", onOutside);
    document.addEventListener("keydown", onEscape);
    return () => {
      document.removeEventListener("pointerdown", onOutside);
      document.removeEventListener("keydown", onEscape);
    };
  }, [notificationsOpen]);

  useEffect(() => { setNotificationsOpen(false); }, [currentWorkspaceId]);

  const openNotification = (event: DirectLiveEvent) => {
    setNotificationsOpen(false);
    openConversation(event.conversation_id);
  };

  return (
    <header className="mobile-safe-top sticky top-0 z-50 min-w-0 border-b border-border-subtle bg-canvas px-3 py-2 text-text-primary sm:px-4 lg:static lg:h-[var(--topbar-height)] lg:bg-surface-1/95 lg:px-5 lg:py-0 lg:backdrop-blur-xl" data-shell-topbar>
      <div className="mobile-topbar-compact flex w-full min-w-0 items-center gap-2 sm:gap-3 lg:h-full lg:gap-3">
        <IconButton className="lg:hidden" onClick={onOpenMenu} aria-label={t("mobileTopbar.openNavigation")}>
          <Menu className="h-5 w-5" />
        </IconButton>

        <div className="mobile-brand-lockup flex min-w-0 flex-1 items-center gap-2.5 md:hidden" data-mobile-brand-lockup>
          <BrandIcon className="h-9 w-9 shrink-0" priority unoptimized />
          <div className="mobile-brand-copy min-w-0 leading-tight">
            <p className="mobile-brand-title truncate text-base font-bold tracking-tight text-text-primary">Sellora</p>
            <p className="truncate text-xs font-medium text-text-secondary">{currentWorkspace?.workspace_name ?? t("accountMenu.workspace")}</p>
          </div>
        </div>

        <div className="min-w-0 shrink-0 md:flex md:min-w-[190px] md:flex-1" data-topbar-search-group>
          <GlobalSearch workspaceId={currentWorkspaceId} />
        </div>

        <div className="hidden shrink-0 lg:block" data-topbar-feedback><FeedbackDialog workspaceId={currentWorkspaceId}
          buttonClassName="grid h-10 w-10 place-items-center rounded-xl border border-border-subtle bg-surface-2 text-text-secondary transition hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
          buttonContent={<><MessageSquare aria-hidden="true" className="h-[18px] w-[18px]" /><span className="sr-only">{t("feedback.button")}</span></>} /></div>
        <div className="hidden shrink-0 lg:block"><LanguageSwitcher compact /></div>
        <div className="hidden shrink-0 lg:block"><ThemeToggle compact /></div>
        <div ref={notificationRef} className="relative shrink-0" data-topbar-notifications>
          <IconButton aria-label={t("topbar.notifications")} aria-expanded={notificationsOpen} onClick={() => setNotificationsOpen((value) => !value)} data-direct-notification-bell>
            <Bell className="h-5 w-5" />
            {bellCount > 0 ? <span className="absolute -right-1.5 -top-1.5 grid min-h-5 min-w-5 place-items-center rounded-full bg-rose-500 px-1 text-[0.65rem] font-black text-white">{bellCount > 99 ? "99+" : bellCount}</span> : null}
          </IconButton>
          {notificationsOpen ? (
            <div className="fixed inset-x-3 top-[calc(3.75rem+env(safe-area-inset-top))] z-[90] max-h-[72dvh] overflow-hidden rounded-2xl border border-border-subtle bg-surface-1 shadow-2xl sm:absolute sm:inset-x-auto sm:right-0 sm:top-12 sm:w-[min(92vw,380px)]" data-direct-notification-center>
              <div className="flex items-start justify-between gap-3 border-b border-border-subtle p-3 sm:p-4">
                <div><p className="text-sm font-semibold text-text-primary">{t("topbar.notifications")}</p><p className={`mt-1 text-xs font-semibold ${isError ? "text-rose-600" : isLive ? "text-emerald-600" : "text-amber-600"}`}>{isError ? "Live-зʼєднання тимчасово недоступне" : isLive ? "Live-оновлення активні" : "Підключення до live-оновлень…"}</p></div>
                {summary?.order_intent_count ? <span className="rounded-full bg-amber-500/15 px-2 py-1 text-xs font-black text-amber-700">Замовлення: {summary.order_intent_count}</span> : null}
              </div>
              {saleCandidates.length > 0 ? (
                <div className="border-b border-border-subtle p-3">
                  <p className="mb-2 text-xs font-bold text-amber-700">Відправлення на перевірку продажу: {saleCandidates.length}</p>
                  {saleCandidates.slice(0, 5).map((sale) => (
                    <button key={sale.document_id} type="button"
                      onClick={() => { setNotificationsOpen(false); router.push(`/shipments/confirmations?document=${encodeURIComponent(sale.document_id)}`); }}
                      className="flex min-h-11 w-full items-center justify-between gap-2 rounded-lg px-2 text-left text-sm transition hover:bg-surface-hover">
                      <span className="truncate">ТТН {sale.tracking_masked} · {sale.customer_instagram ? `@${sale.customer_instagram.replace(/^@/, "")}` : "покупець"}</span>
                      <span className="text-xs font-semibold text-primary">Перевірити</span>
                    </button>
                  ))}
                </div>
              ) : null}
              {permission === "default" ? <div className="border-b border-border-subtle p-3"><button type="button" onClick={() => void requestBrowserNotifications()} className="min-h-11 w-full rounded-2xl bg-primary/15 px-3 text-sm font-black text-primary hover:bg-primary/20">Увімкнути системні сповіщення</button></div> : null}
              <div className="max-h-[min(55dvh,370px)] overflow-y-auto p-2">
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

        {canCreateOrder ? (
          <button type="button" onClick={createOrder} aria-label={t("topbar.createOrder")} data-topbar-create-order
            className="inline-flex min-h-10 shrink-0 items-center justify-center gap-1.5 rounded-xl bg-primary px-3 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring">
            <Plus aria-hidden="true" className="h-[18px] w-[18px]" />
            <span className="hidden whitespace-nowrap 2xl:inline">{t("topbar.create")}</span>
          </button>
        ) : null}
        <ProfileMenu currentUser={currentUser} currentWorkspace={currentWorkspace} currentWorkspaceId={currentWorkspaceId} memberships={validMemberships} onLogout={onLogout} onSwitchWorkspace={onSwitchWorkspace} onWorkspaceCreated={onWorkspaceCreated} />
      </div>

      <MobileMoreSheet open={mobileMoreOpen} currentUser={currentUser} currentWorkspace={currentWorkspace} currentWorkspaceId={currentWorkspaceId} memberships={validMemberships} onClose={onCloseMobileMore} onLogout={onLogout} onSwitchWorkspace={onSwitchWorkspace} onWorkspaceCreated={onWorkspaceCreated} />
    </header>
  );
}

// Mobile UI contract: controlled-more-sheet shared-icon-buttons minimum-touch-target-44.
