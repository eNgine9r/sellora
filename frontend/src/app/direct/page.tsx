/* eslint-disable @next/next/no-img-element */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BadgeCheck,
  Bot,
  CheckCircle2,
  MessageCircle,
  RefreshCw,
  Send,
  ShoppingBag,
  Sparkles,
  UserRound,
  Users,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { Button, WorkspaceHeader, WorkspacePage } from "@/components/crm-workspace";
import { useDirectLive } from "@/components/direct-live-provider";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { fetchAISuggestions } from "@/services/ai";
import {
  fetchDirectConversations,
  fetchDirectMessages,
  fetchInstagramHistorySync,
  markDirectConversationRead,
  prepareDirectReply,
  refreshDirectParticipantProfile,
  runDirectAnalysis,
  sendDirectReply,
  startInstagramHistorySync,
} from "@/services/direct";
import { fetchInstagramStatus } from "@/services/meta-instagram";
import { AISuggestion } from "@/types/ai";
import { DirectConversation, DirectMessage, InstagramHistorySync } from "@/types/direct";

const ACTIVE_HISTORY_STATUSES = new Set(["PENDING", "RUNNING", "RETRY_PENDING"]);

export default function DirectPage() {
  const { t } = useI18n();
  const { currentWorkspace } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isLive, isError: liveError, orderIntentConversationIds } = useDirectLive();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [replyText, setReplyText] = useState("");
  const profileRefreshAttempted = useRef(new Set<string>());
  const readAttempted = useRef(new Set<string>());

  const workspaceId = currentWorkspace?.workspace_id;
  const conversationsQuery = useQuery({
    queryKey: ["direct-conversations", workspaceId],
    queryFn: fetchDirectConversations,
    enabled: Boolean(workspaceId),
    refetchInterval: 2000,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
  });
  const selectedConversation = useMemo(
    () => conversationsQuery.data?.find((item) => item.id === selectedId) ?? conversationsQuery.data?.[0],
    [conversationsQuery.data, selectedId],
  );
  const messagesQuery = useQuery({
    queryKey: ["direct-messages", workspaceId, selectedConversation?.id],
    queryFn: () => fetchDirectMessages(selectedConversation!.id),
    enabled: Boolean(selectedConversation?.id),
    refetchInterval: 1500,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
  });
  const suggestionsQuery = useQuery({
    queryKey: ["ai-suggestions", workspaceId, selectedConversation?.id],
    queryFn: () => fetchAISuggestions(selectedConversation!.id),
    enabled: Boolean(selectedConversation?.id),
  });
  const statusQuery = useQuery({
    queryKey: ["instagram-connection-status", workspaceId],
    queryFn: fetchInstagramStatus,
    enabled: Boolean(workspaceId),
  });
  const historyQuery = useQuery({
    queryKey: ["instagram-history-sync", workspaceId],
    queryFn: fetchInstagramHistorySync,
    enabled: Boolean(workspaceId),
    refetchInterval: 3000,
  });

  const analysisMutation = useMutation({
    mutationFn: () => runDirectAnalysis(selectedConversation!.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ai-suggestions", workspaceId, selectedConversation?.id] }),
  });
  const prepareMutation = useMutation({ mutationFn: () => prepareDirectReply(selectedConversation!.id, replyText) });
  const sendMutation = useMutation({
    mutationFn: () => sendDirectReply(selectedConversation!.id, replyText, crypto.randomUUID()),
    onSuccess: () => {
      setReplyText("");
      void queryClient.invalidateQueries({ queryKey: ["direct-messages", workspaceId, selectedConversation?.id] });
      void queryClient.invalidateQueries({ queryKey: ["direct-conversations", workspaceId] });
    },
  });
  const profileMutation = useMutation({
    mutationFn: (conversationId: string) => refreshDirectParticipantProfile(conversationId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["direct-conversations", workspaceId] }),
  });
  const historyMutation = useMutation({
    mutationFn: () => startInstagramHistorySync(100, 20),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["instagram-history-sync", workspaceId] }),
  });
  const readMutation = useMutation({
    mutationFn: (conversationId: string) => markDirectConversationRead(conversationId),
    onSuccess: (_conversation, conversationId) => {
      void queryClient.invalidateQueries({ queryKey: ["direct-conversations", workspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["direct-live-summary", workspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["direct-messages", workspaceId, conversationId] });
    },
  });

  const historyActive = Boolean(historyQuery.data && ACTIVE_HISTORY_STATUSES.has(historyQuery.data.status));

  useEffect(() => {
    setSelectedId(null);
    setReplyText("");
    profileRefreshAttempted.current.clear();
    readAttempted.current.clear();
  }, [workspaceId]);

  useEffect(() => {
    if (!conversationsQuery.data?.length || typeof window === "undefined") return;
    const requestedId = new URLSearchParams(window.location.search).get("conversation");
    if (requestedId && conversationsQuery.data.some((item) => item.id === requestedId)) {
      setSelectedId(requestedId);
    }
  }, [conversationsQuery.data]);

  useEffect(() => {
    const draft = suggestionsQuery.data?.find((item) => item.draft_text)?.draft_text;
    if (draft && !replyText) setReplyText(draft);
  }, [suggestionsQuery.data, replyText]);

  useEffect(() => {
    if (!selectedConversation || selectedConversation.channel !== "INSTAGRAM") return;
    if (selectedConversation.participant_profile_status === "READY") return;
    if (profileRefreshAttempted.current.has(selectedConversation.id)) return;
    const retryAt = selectedConversation.participant_profile_next_retry_at
      ? new Date(selectedConversation.participant_profile_next_retry_at).getTime()
      : 0;
    if (retryAt > Date.now()) return;
    profileRefreshAttempted.current.add(selectedConversation.id);
    profileMutation.mutate(selectedConversation.id);
  }, [selectedConversation, profileMutation]);

  useEffect(() => {
    if (!selectedConversation || selectedConversation.unread_count <= 0) return;
    const readKey = `${selectedConversation.id}:${selectedConversation.last_message_at ?? selectedConversation.unread_count}`;
    if (readAttempted.current.has(readKey)) return;
    readAttempted.current.add(readKey);
    readMutation.mutate(selectedConversation.id);
  }, [readMutation, selectedConversation]);

  useEffect(() => {
    if (!historyQuery.data || !["COMPLETED", "PARTIAL"].includes(historyQuery.data.status)) return;
    queryClient.invalidateQueries({ queryKey: ["direct-conversations", workspaceId] });
    if (selectedConversation?.id) {
      queryClient.invalidateQueries({ queryKey: ["direct-messages", workspaceId, selectedConversation.id] });
    }
  }, [historyQuery.data?.status, queryClient, selectedConversation?.id, workspaceId]);

  const handleSelectConversation = (conversationId: string) => {
    setSelectedId(conversationId);
    router.replace(`/direct?conversation=${encodeURIComponent(conversationId)}`, { scroll: false });
  };

  return (
    <WorkspacePage className="min-h-full">
      <WorkspaceHeader
        eyebrow={t("direct.kicker")}
        title={t("direct.title")}
        description={t("direct.description")}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <span className={`inline-flex min-h-10 items-center gap-2 rounded-2xl border px-3 text-xs font-black ${liveError ? "border-rose-500/30 bg-rose-500/10 text-rose-600" : isLive ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600" : "border-amber-500/30 bg-amber-500/10 text-amber-600"}`} data-direct-live-status>
              {liveError ? <WifiOff className="h-4 w-4" /> : <Wifi className={`h-4 w-4 ${isLive ? "" : "animate-pulse"}`} />}
              {liveError ? "Live недоступний" : isLive ? "Live" : "Підключення…"}
            </span>
            <Button
              variant="secondary"
              onClick={() => historyMutation.mutate()}
              disabled={historyMutation.isPending || historyActive || statusQuery.data?.status !== "CONNECTED"}
            >
              <RefreshCw className={`h-4 w-4 ${historyMutation.isPending || historyActive ? "animate-spin" : ""}`} />
              {historyActive ? "Синхронізація історії…" : "Синхронізувати історію"}
            </Button>
            <Button onClick={() => conversationsQuery.refetch()}>
              <RefreshCw className="h-4 w-4" />
              {t("actions.refresh")}
            </Button>
          </div>
        }
      />

      <HistorySyncBanner sync={historyQuery.data} loading={historyQuery.isLoading} />

      <div className="lg:hidden">
        <button
          type="button"
          onClick={() => setAiPanelOpen(true)}
          className="min-h-11 w-full rounded-2xl border border-border-subtle bg-surface-1 px-4 py-2 text-sm font-black text-primary shadow-[var(--shadow-card)]"
        >
          {t("direct.openAiPanel")}
        </button>
      </div>

      <section
        className="grid min-h-[calc(100dvh-var(--topbar-height,72px)-190px)] min-w-0 gap-4 lg:grid-cols-[minmax(260px,320px)_minmax(0,1fr)_minmax(320px,380px)]"
        data-direct-shell-content
      >
        <ConversationList
          loading={conversationsQuery.isLoading}
          error={conversationsQuery.isError}
          conversations={conversationsQuery.data ?? []}
          selectedId={selectedConversation?.id ?? null}
          onSelect={handleSelectConversation}
          instagramStatus={statusQuery.data}
          orderIntentConversationIds={orderIntentConversationIds}
          isLive={isLive}
          liveError={liveError}
        />
        <MessageThread
          conversation={selectedConversation}
          loading={messagesQuery.isLoading}
          error={messagesQuery.isError}
          messages={messagesQuery.data ?? []}
          replyText={replyText}
          setReplyText={setReplyText}
          onPrepare={() => prepareMutation.mutate()}
          onSend={() => sendMutation.mutate()}
          onRefreshProfile={() => selectedConversation && profileMutation.mutate(selectedConversation.id)}
          profileRefreshing={profileMutation.isPending}
          sendDisabled={
            !selectedConversation
            || selectedConversation.channel !== "INSTAGRAM"
            || statusQuery.data?.status !== "CONNECTED"
            || sendMutation.isPending
          }
          prepareResult={prepareMutation.data}
          sendPending={sendMutation.isPending}
          noAutoSend={t("direct.noAutoSend")}
        />
        <div className="hidden lg:block">
          <AiPanel
            loading={suggestionsQuery.isLoading}
            suggestions={suggestionsQuery.data ?? []}
            onAnalyze={() => analysisMutation.mutate()}
            analyzing={analysisMutation.isPending}
            connectionStatus={statusQuery.data?.status ?? "DISCONNECTED"}
          />
        </div>
      </section>

      {aiPanelOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label={t("direct.aiPanel")}>
          <button
            type="button"
            className="absolute inset-0 bg-[var(--overlay-background)] backdrop-blur-sm"
            aria-label={t("actions.close")}
            onClick={() => setAiPanelOpen(false)}
          />
          <aside className="absolute inset-y-0 right-0 flex w-[92vw] max-w-md flex-col overflow-hidden bg-surface-1 shadow-2xl">
            <header className="flex items-center justify-between border-b border-border-subtle p-4">
              <div className="flex items-center gap-2">
                <Bot className="h-5 w-5 text-primary" />
                <h2 className="font-black">{t("direct.aiPanel")}</h2>
              </div>
              <button
                type="button"
                className="rounded-2xl p-2 text-text-secondary hover:bg-surface-hover"
                onClick={() => setAiPanelOpen(false)}
                aria-label={t("actions.close")}
              >
                <X className="h-5 w-5" />
              </button>
            </header>
            <div className="sellora-scrollbar min-h-0 flex-1 overflow-y-auto p-4">
              <AiPanel
                loading={suggestionsQuery.isLoading}
                suggestions={suggestionsQuery.data ?? []}
                onAnalyze={() => analysisMutation.mutate()}
                analyzing={analysisMutation.isPending}
                connectionStatus={statusQuery.data?.status ?? "DISCONNECTED"}
                embedded
              />
            </div>
          </aside>
        </div>
      ) : null}
    </WorkspacePage>
  );
}

function HistorySyncBanner({ sync, loading }: { sync?: InstagramHistorySync | null; loading: boolean }) {
  if (loading || !sync) return null;
  const active = ACTIVE_HISTORY_STATUSES.has(sync.status);
  const statusLabel: Record<string, string> = {
    PENDING: "Очікує запуску",
    RUNNING: "Синхронізація виконується",
    RETRY_PENDING: "Meta обмежила запити — повтор буде автоматично",
    COMPLETED: "Історію синхронізовано",
    PARTIAL: "Історію синхронізовано частково",
    FAILED_SAFE: "Синхронізацію безпечно зупинено",
  };
  return (
    <section className="rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-4 shadow-[var(--shadow-card)]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-black">{statusLabel[sync.status] ?? sync.status}</p>
          <p className="mt-1 text-sm text-text-secondary">
            Діалоги: {sync.conversations_synced}/{sync.conversations_discovered} · Нові повідомлення: {sync.messages_imported} · Уже були в Sellora: {sync.messages_existing}
          </p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-black ${active ? "bg-violet-500/15 text-primary" : sync.status === "FAILED_SAFE" ? "bg-rose-500/15 text-rose-600" : "bg-emerald-500/15 text-emerald-700"}`}>
          {sync.status}
        </span>
      </div>
      {sync.messages_unavailable > 0 || sync.error_count > 0 ? (
        <p className="mt-2 text-xs font-semibold text-amber-700">
          Недоступні старі повідомлення: {sync.messages_unavailable} · Помилки: {sync.error_count}. Нові webhooks продовжують працювати.
        </p>
      ) : null}
    </section>
  );
}

function ParticipantAvatar({ conversation, size = "md" }: { conversation: DirectConversation; size?: "sm" | "md" | "lg" }) {
  const className = size === "lg" ? "h-16 w-16 text-xl" : size === "sm" ? "h-10 w-10 text-sm" : "h-12 w-12 text-base";
  const label = conversation.participant_display_name ?? conversation.participant_username ?? "Instagram customer";
  return (
    <span className={`relative grid shrink-0 place-items-center overflow-hidden rounded-full bg-primary/15 font-black text-primary ${className}`}>
      <span>{label.slice(0, 1).toUpperCase()}</span>
      {conversation.participant_profile_picture_url ? (
        <img
          src={conversation.participant_profile_picture_url}
          alt={label}
          className="absolute inset-0 h-full w-full object-cover"
          referrerPolicy="no-referrer"
          onError={(event) => { event.currentTarget.style.display = "none"; }}
        />
      ) : null}
    </span>
  );
}

function ConversationList({
  loading,
  error,
  conversations,
  selectedId,
  onSelect,
  instagramStatus,
  orderIntentConversationIds,
  isLive,
  liveError,
}: {
  loading: boolean;
  error: boolean;
  conversations: DirectConversation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  instagramStatus?: { status: string; webhook_active?: boolean; token_present?: boolean };
  orderIntentConversationIds: Set<string>;
  isLive: boolean;
  liveError: boolean;
}) {
  const orderedConversations = useMemo(
    () => [...conversations].sort((left, right) => {
      const orderDifference = Number(orderIntentConversationIds.has(right.id)) - Number(orderIntentConversationIds.has(left.id));
      if (orderDifference) return orderDifference;
      const unreadDifference = right.unread_count - left.unread_count;
      if (unreadDifference) return unreadDifference;
      return new Date(right.last_message_at ?? 0).getTime() - new Date(left.last_message_at ?? 0).getTime();
    }),
    [conversations, orderIntentConversationIds],
  );

  if (loading) return <aside className="rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-3"><LoadingSkeleton /></aside>;
  if (error) return <aside className="rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-3"><ErrorState title="Не вдалося завантажити Direct" description="Оновіть сторінку або перевірте workspace." /></aside>;
  return (
    <aside className="min-w-0 rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-3 shadow-[var(--shadow-card)]">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="font-black">Діалоги</h2>
        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-black ${liveError ? "bg-rose-500/15 text-rose-600" : isLive ? "bg-emerald-500/15 text-emerald-600" : "bg-amber-500/15 text-amber-600"}`}>
          {liveError ? <WifiOff className="h-3 w-3" /> : <Wifi className="h-3 w-3" />}
          {liveError ? "Offline" : isLive ? "Live" : "…"}
        </span>
      </div>
      <input className="mb-3 min-h-11 w-full rounded-2xl border border-border-subtle bg-surface-2 px-3 text-sm" placeholder="Пошук за іменем або username" />
      <div className="flex flex-wrap gap-2 pb-3 text-xs font-bold text-text-secondary"><span>Open</span><span>Unread</span><span>Instagram</span><span>Тестовий діалог</span></div>
      {orderedConversations.length === 0 ? <DirectEmptyState instagramStatus={instagramStatus} /> : (
        <div className="space-y-2">
          {orderedConversations.map((item) => {
            const orderIntent = orderIntentConversationIds.has(item.id);
            return (
              <button type="button" key={item.id} onClick={() => onSelect(item.id)} className={`w-full rounded-2xl border p-3 text-left transition ${orderIntent ? "border-amber-500/50 bg-amber-500/10" : selectedId === item.id ? "border-primary bg-primary/10" : "border-border-subtle bg-surface-2"}`}>
                <div className="flex items-start gap-3">
                  <ParticipantAvatar conversation={item} size="sm" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <h3 className="flex items-center gap-1 truncate font-black">{item.participant_display_name ?? "Instagram customer"}{item.participant_is_verified_user ? <BadgeCheck className="h-4 w-4 shrink-0 text-sky-500" /> : null}</h3>
                        <p className="truncate text-xs text-text-muted">{item.participant_username ? `@${item.participant_username}` : item.participant_scoped_id ?? "—"}</p>
                      </div>
                      {item.unread_count ? <span className="rounded-full bg-rose-500 px-2 py-0.5 text-xs font-black text-white">{item.unread_count}</span> : null}
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {orderIntent ? <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2 py-1 text-xs font-black text-amber-700"><ShoppingBag className="h-3 w-3" />Ймовірне замовлення</span> : null}
                      <span className="rounded-full bg-violet-500/15 px-2 py-1 text-xs font-bold text-primary">{item.channel === "INSTAGRAM" ? "Instagram" : "Тестовий діалог"}</span>
                      <span className="rounded-full bg-emerald-500/15 px-2 py-1 text-xs font-bold text-emerald-600">{item.status}</span>
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </aside>
  );
}

function DirectEmptyState({ instagramStatus }: { instagramStatus?: { status: string; webhook_active?: boolean; token_present?: boolean } }) {
  if (!instagramStatus || instagramStatus.status === "DISCONNECTED" || !instagramStatus.token_present) return <EmptyState title="Instagram не підключено" description="Підключіть Instagram Direct в інтеграціях або створіть тестовий діалог через backend synthetic API." />;
  if (!instagramStatus.webhook_active) return <EmptyState title="Webhook неактивний" description="Instagram підключено, але Meta ще не надсилає повідомлення в Sellora. Активуйте webhook в налаштуваннях інтеграції." />;
  return <EmptyState title="Повідомлень ще немає" description="Webhook активний. Надішліть нове Direct-повідомлення з тестового Instagram акаунта або синхронізуйте доступну історію." />;
}

type PrepareResult = { ready: boolean; blockers: string[]; warnings: string[]; message_preview: string };

function MessageThread({
  conversation,
  loading,
  error,
  messages,
  replyText,
  setReplyText,
  onPrepare,
  onSend,
  onRefreshProfile,
  profileRefreshing,
  sendDisabled,
  prepareResult,
  sendPending,
  noAutoSend,
}: {
  conversation?: DirectConversation | null;
  loading: boolean;
  error: boolean;
  messages: DirectMessage[];
  replyText: string;
  setReplyText: (value: string) => void;
  onPrepare: () => void;
  onSend: () => void;
  onRefreshProfile: () => void;
  profileRefreshing: boolean;
  sendDisabled: boolean;
  prepareResult?: PrepareResult;
  sendPending: boolean;
  noAutoSend: string;
}) {
  const scrollContainer = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = scrollContainer.current;
    if (!element) return;
    element.scrollTo({ top: element.scrollHeight, behavior: messages.length > 1 ? "smooth" : "auto" });
  }, [conversation?.id, messages.length]);

  if (!conversation) return <section className="rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-4"><EmptyState title="Оберіть діалог" description="Повідомлення та AI-підказки зʼявляться після вибору розмови." /></section>;
  return (
    <section className="flex min-h-[520px] min-w-0 flex-col rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 shadow-[var(--shadow-card)]">
      <ParticipantProfileCard conversation={conversation} onRefresh={onRefreshProfile} refreshing={profileRefreshing} />
      <div ref={scrollContainer} className="sellora-scrollbar flex-1 space-y-3 overflow-y-auto p-4" data-direct-live-thread>
        {loading ? <LoadingSkeleton /> : null}
        {error ? <ErrorState title="Не вдалося завантажити повідомлення" description="Спробуйте оновити діалог." /> : null}
        {!loading && !error && messages.length === 0 ? <EmptyState title="Повідомлень ще немає" description="Нові Instagram webhooks або імпортована історія зʼявляться тут." /> : null}
        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.direction === "OUTBOUND" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[82%] rounded-3xl px-4 py-3 text-sm ${message.direction === "OUTBOUND" ? "bg-primary/15 text-text-primary" : "bg-surface-2"}`}>
              <p className="mb-1 text-xs font-black text-text-muted">{message.direction} · {messageStatusLabel(message)}</p>
              <p>{message.text}</p>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-text-muted">
                {message.edit_count ? <span>ред. {message.edit_count}</span> : null}
                {message.reaction ? <span className="rounded-full bg-surface-1 px-2 py-0.5">{message.reaction}</span> : null}
              </div>
            </div>
          </div>
        ))}
      </div>
      <footer className="border-t border-border-subtle p-3">
        <div className="mb-2 rounded-2xl border border-dashed border-border-subtle p-3 text-sm text-text-muted">{`Чернетка AI — не відправлено. ${noAutoSend}`}</div>
        <textarea value={replyText} onChange={(event) => setReplyText(event.target.value)} className="min-h-24 w-full rounded-2xl border border-border-subtle bg-surface-2 p-3 text-sm" placeholder="Відповідь менеджера" />
        <div className="mt-2 flex flex-wrap gap-2">
          <Button variant="secondary" onClick={onPrepare} disabled={!replyText}>Перевірити відправлення</Button>
          <Button onClick={onSend} disabled={sendDisabled || !replyText}>{sendPending ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}Підтвердити send</Button>
        </div>
        {prepareResult ? <p className="mt-2 text-sm text-text-secondary">{prepareResult.ready ? "Готово до ручного підтвердження" : `Блокери: ${prepareResult.blockers.join(", ")}`}</p> : null}
      </footer>
    </section>
  );
}

function messageStatusLabel(message: DirectMessage) {
  if (message.seen_at || message.delivery_status === "SEEN") return "Прочитано";
  if (message.direction === "OUTBOUND" && message.delivery_status === "PROVIDER_ACCEPTED") return "Прийнято Meta";
  if (message.direction === "INBOUND" && message.delivery_status === "RECEIVED") return "Отримано";
  if (message.delivery_status === "FAILED") return "Помилка";
  return message.delivery_status ?? "Статус невідомий";
}

function ParticipantProfileCard({ conversation, onRefresh, refreshing }: { conversation: DirectConversation; onRefresh: () => void; refreshing: boolean }) {
  const followers = conversation.participant_follower_count == null ? null : new Intl.NumberFormat("uk-UA").format(conversation.participant_follower_count);
  const profileReady = conversation.participant_profile_status === "READY";
  return (
    <header className="border-b border-border-subtle p-4">
      <div className="flex flex-wrap items-start gap-4">
        <ParticipantAvatar conversation={conversation} size="lg" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="truncate text-lg font-black">{conversation.participant_display_name ?? "Instagram customer"}</h2>
            {conversation.participant_is_verified_user ? <span className="inline-flex items-center gap-1 rounded-full bg-sky-500/15 px-2 py-1 text-xs font-bold text-sky-600"><BadgeCheck className="h-3.5 w-3.5" />Verified</span> : null}
          </div>
          <p className="text-sm text-text-secondary">{conversation.participant_username ? `@${conversation.participant_username}` : "Username поки недоступний"}</p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs font-bold text-text-secondary">
            {followers ? <span className="inline-flex items-center gap-1 rounded-full bg-surface-2 px-2 py-1"><Users className="h-3.5 w-3.5" />{followers} підписників</span> : null}
            {conversation.participant_is_user_follow_business === true ? <span className="rounded-full bg-emerald-500/15 px-2 py-1 text-emerald-700">Підписаний на магазин</span> : null}
            {conversation.participant_is_business_follow_user === true ? <span className="rounded-full bg-violet-500/15 px-2 py-1 text-primary">Магазин підписаний</span> : null}
          </div>
        </div>
        {conversation.channel === "INSTAGRAM" ? <Button variant="secondary" onClick={onRefresh} disabled={refreshing}>{refreshing ? <RefreshCw className="h-4 w-4 animate-spin" /> : <UserRound className="h-4 w-4" />}{profileReady ? "Оновити профіль" : "Завантажити профіль"}</Button> : null}
      </div>
      <p className="mt-3 text-sm text-text-secondary">{conversation.channel === "INSTAGRAM" ? "Instagram" : "Тестовий діалог"} · {conversation.messaging_window_expires_at ? `вікно до ${conversation.messaging_window_expires_at}` : "відправлення недоступне без активного messaging window"}</p>
      {conversation.channel === "INSTAGRAM" && !profileReady ? <p className="mt-2 rounded-2xl bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-700">{conversation.participant_profile_status === "RETRY_PENDING" ? "Meta тимчасово не відповідає. Дані профілю буде оновлено повторно." : conversation.participant_profile_status === "UNAVAILABLE" ? "Meta не надала дані профілю. Повідомлення й відповіді продовжують працювати з безпечним fallback." : "Завантажуємо дозволену Meta інформацію про потенційного клієнта."}</p> : null}
    </header>
  );
}

function AiPanel({ loading, suggestions, onAnalyze, analyzing, connectionStatus, embedded = false }: { loading: boolean; suggestions: AISuggestion[]; onAnalyze: () => void; analyzing: boolean; connectionStatus: string; embedded?: boolean }) {
  return <aside className={`${embedded ? "" : "h-full"} min-w-0 rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-4 shadow-[var(--shadow-card)]`} data-direct-ai-panel>{!embedded ? <div className="mb-4 flex items-center gap-2"><Bot className="h-5 w-5 text-primary" /><h2 className="font-black">AI Intelligence</h2></div> : null}<div className="mb-3 rounded-2xl bg-surface-2 p-3 text-sm">Instagram connection: {connectionStatus}</div><Button onClick={onAnalyze} disabled={analyzing}>{analyzing ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}Запустити AI аналіз</Button><div className="mt-4 space-y-3 text-sm">{loading ? <LoadingSkeleton /> : null}{!loading && suggestions.length === 0 ? <EmptyState title="AI-підказок ще немає" description="Запустіть аналіз для поточного inbound text message." /> : null}{suggestions.map((suggestion) => <Card key={suggestion.id} icon={<MessageCircle />} title={suggestion.title ?? suggestion.suggestion_type} body={suggestion.draft_text ?? suggestion.summary ?? "Чернетка очікує перегляду менеджером."} />)}<Card title="Безпека" body="AI не надсилає Instagram повідомлення автоматично і не змінює CRM без підтвердження." /></div></aside>;
}

function Card({ title, body, icon }: { title: string; body: string; icon?: React.ReactNode }) {
  return <section className="rounded-2xl border border-border-subtle bg-surface-2 p-3"><div className="mb-1 flex items-center gap-2 font-black">{icon ? <span className="h-4 w-4 text-primary">{icon}</span> : <CheckCircle2 className="h-4 w-4 text-emerald-500" />}{title}</div><p className="text-text-secondary">{body}</p></section>;
}
