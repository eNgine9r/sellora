"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { BellRing, ShoppingBag, X } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { fetchDirectLiveSummary } from "@/services/direct";
import { DirectLiveEvent, DirectLiveSummary } from "@/types/direct";


type BrowserNotificationPermission = NotificationPermission | "unsupported";

type DirectLiveContextValue = {
  summary?: DirectLiveSummary;
  isLive: boolean;
  isError: boolean;
  permission: BrowserNotificationPermission;
  requestBrowserNotifications: () => Promise<BrowserNotificationPermission>;
  openConversation: (conversationId: string) => void;
  orderIntentConversationIds: Set<string>;
};

const DirectLiveContext = createContext<DirectLiveContextValue>({
  isLive: false,
  isError: false,
  permission: "unsupported",
  requestBrowserNotifications: async () => "unsupported",
  openConversation: () => undefined,
  orderIntentConversationIds: new Set<string>(),
});

function eventTitle(event: DirectLiveEvent) {
  return event.order_intent ? "Ймовірне нове замовлення" : "Нове Instagram повідомлення";
}

function participantLabel(event: DirectLiveEvent) {
  return event.participant_display_name
    ?? (event.participant_username ? `@${event.participant_username}` : null)
    ?? "Клієнт Instagram";
}

export function DirectLiveProvider({ workspaceId, children }: { workspaceId: string | null; children: ReactNode }) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const pathname = usePathname();
  const initialized = useRef(false);
  const knownMessageIds = useRef(new Set<string>());
  const [toastEvent, setToastEvent] = useState<DirectLiveEvent | null>(null);
  const [permission, setPermission] = useState<BrowserNotificationPermission>("unsupported");

  const liveQuery = useQuery({
    queryKey: ["direct-live-summary", workspaceId],
    queryFn: fetchDirectLiveSummary,
    enabled: Boolean(workspaceId),
    refetchInterval: 2000,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
    staleTime: 1000,
    retry: 3,
  });

  useEffect(() => {
    initialized.current = false;
    knownMessageIds.current.clear();
    setToastEvent(null);
  }, [workspaceId]);

  useEffect(() => {
    if (typeof window === "undefined" || !("Notification" in window)) {
      setPermission("unsupported");
      return;
    }
    setPermission(Notification.permission);
  }, []);

  const openConversation = useCallback((conversationId: string) => {
    router.push(`/direct?conversation=${encodeURIComponent(conversationId)}`);
  }, [router]);

  useEffect(() => {
    const summary = liveQuery.data;
    if (!summary || !workspaceId) return;

    const incomingIds = summary.events.map((event) => event.message_id);
    if (!initialized.current) {
      incomingIds.forEach((id) => knownMessageIds.current.add(id));
      initialized.current = true;
      return;
    }

    const fresh = summary.events
      .filter((event) => !knownMessageIds.current.has(event.message_id))
      .sort((left, right) => new Date(left.received_at).getTime() - new Date(right.received_at).getTime());
    incomingIds.forEach((id) => knownMessageIds.current.add(id));
    if (fresh.length === 0) return;

    void queryClient.invalidateQueries({ queryKey: ["direct-conversations", workspaceId] });
    void queryClient.invalidateQueries({
      predicate: (query) => query.queryKey[0] === "direct-messages" && query.queryKey[1] === workspaceId,
    });

    const newest = fresh[fresh.length - 1];
    setToastEvent(newest);

    if (typeof window !== "undefined" && "Notification" in window && Notification.permission === "granted") {
      for (const event of fresh) {
        if (!document.hidden && pathname.startsWith("/direct")) continue;
        const notification = new Notification(eventTitle(event), {
          body: `${participantLabel(event)}: ${event.text_preview}`,
          tag: `sellora-direct-${event.message_id}`,
        });
        notification.onclick = () => {
          window.focus();
          openConversation(event.conversation_id);
          notification.close();
        };
      }
    }
  }, [liveQuery.data, openConversation, pathname, queryClient, workspaceId]);

  useEffect(() => {
    if (!toastEvent) return;
    const timeout = window.setTimeout(() => setToastEvent(null), 8000);
    return () => window.clearTimeout(timeout);
  }, [toastEvent]);

  const requestBrowserNotifications = useCallback(async (): Promise<BrowserNotificationPermission> => {
    if (typeof window === "undefined" || !("Notification" in window)) {
      setPermission("unsupported");
      return "unsupported";
    }
    const result = await Notification.requestPermission();
    setPermission(result);
    return result;
  }, []);

  const orderIntentConversationIds = useMemo(
    () => new Set((liveQuery.data?.events ?? []).filter((event) => event.order_intent).map((event) => event.conversation_id)),
    [liveQuery.data?.events],
  );

  const value = useMemo<DirectLiveContextValue>(() => ({
    summary: liveQuery.data,
    isLive: liveQuery.isSuccess && !liveQuery.isError,
    isError: liveQuery.isError,
    permission,
    requestBrowserNotifications,
    openConversation,
    orderIntentConversationIds,
  }), [liveQuery.data, liveQuery.isError, liveQuery.isSuccess, openConversation, orderIntentConversationIds, permission, requestBrowserNotifications]);

  return (
    <DirectLiveContext.Provider value={value}>
      {children}
      {toastEvent ? (
        <div className="fixed right-4 top-20 z-[80] w-[min(92vw,420px)] overflow-hidden rounded-3xl border border-border-subtle bg-surface-1 shadow-2xl" role="status" aria-live="polite" data-direct-live-toast>
          <button
            type="button"
            onClick={() => openConversation(toastEvent.conversation_id)}
            className="flex w-full items-start gap-3 p-4 text-left transition hover:bg-surface-hover"
          >
            <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-2xl ${toastEvent.order_intent ? "bg-amber-500/15 text-amber-600" : "bg-primary/15 text-primary"}`}>
              {toastEvent.order_intent ? <ShoppingBag className="h-5 w-5" /> : <BellRing className="h-5 w-5" />}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block font-black">{eventTitle(toastEvent)}</span>
              <span className="mt-1 block truncate text-sm font-semibold text-text-secondary">{participantLabel(toastEvent)}</span>
              <span className="mt-1 block line-clamp-2 text-sm text-text-muted">{toastEvent.text_preview}</span>
            </span>
          </button>
          <button type="button" onClick={() => setToastEvent(null)} className="absolute right-2 top-2 rounded-xl p-2 text-text-muted hover:bg-surface-hover" aria-label="Закрити сповіщення">
            <X className="h-4 w-4" />
          </button>
        </div>
      ) : null}
    </DirectLiveContext.Provider>
  );
}

export function useDirectLive() {
  return useContext(DirectLiveContext);
}
