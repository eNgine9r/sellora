/* eslint-disable @next/next/no-img-element */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Clock3,
  Square,
  BadgeCheck,
  Bot,
  CheckCircle2,
  MessageCircle,
  RefreshCw,
  Send,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  UserPlus,
  UserRound,
  Users,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";

import { Button, WorkspaceHeader, WorkspacePage } from "@/components/crm-workspace";
import { useDirectLive } from "@/components/direct-live-provider";
import { DirectOrderEvidenceCard } from "@/components/direct-order-evidence-card";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { fetchAISuggestions } from "@/services/ai";
import {
  ensureDirectCustomer,
  cancelInstagramHistorySync,
  ensureDirectLead,
  confirmDirectOrderEvidence,
  fetchDirectConversations,
  fetchDirectOrderEvidence,
  fetchDirectCustomerAutomation,
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
import {
  DirectConversation,
  DirectOrderEvidence,
  DirectCustomerAutomationState,
  DirectMessage,
  InstagramHistorySync,
} from "@/types/direct";

const ACTIVE_HISTORY_STATUSES = new Set(["PENDING", "RUNNING", "RETRY_PENDING"]);

export default function DirectPage() {
  return <Suspense fallback={<LoadingSkeleton />}><DirectPageContent /></Suspense>;
}

function DirectPageContent() {
  const { t } = useI18n();
  const { currentWorkspace } = useAuth();
  const router = useRouter();
  const requestedConversationId = useSearchParams().get("conversation");
  const [isMobile, setIsMobile] = useState(false);
  const listScrollPosition = useRef(0);
  const queryClient = useQueryClient();
  const { isLive, isError: liveError, orderIntentConversationIds } = useDirectLive();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  // Synchronously track a newly requested dialog before React has rendered
  // its details. Mutations must never run against a stale previous thread.
  const selectionTargetRef = useRef<string | null>(null);
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [historyPanelOpen, setHistoryPanelOpen] = useState(false);
  const [replyText, setReplyText] = useState("");
  const profileRefreshAttempted = useRef(new Set<string>());
  const readAttempted = useRef(new Set<string>());
  const customerAutomationAttempted = useRef(new Set<string>());

  const workspaceId = currentWorkspace?.workspace_id;
  const canManage = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";
  const conversationsQuery = useQuery({
    queryKey: ["direct-conversations", workspaceId],
    queryFn: fetchDirectConversations,
    enabled: Boolean(workspaceId),
    refetchInterval: 2000,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
  });
  useEffect(() => {
    const media = window.matchMedia("(max-width: 1023px)");
    const update = () => setIsMobile(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  const selectedConversation = useMemo(
    () => selectedId
      ? (conversationsQuery.data?.find((item) => item.id === selectedId) ?? null)
      : (isMobile ? null : (conversationsQuery.data?.[0] ?? null)),
    [conversationsQuery.data, isMobile, selectedId],
  );
  const messagesQuery = useQuery({
    queryKey: ["direct-messages", workspaceId, selectedConversation?.id],
    queryFn: () => fetchDirectMessages(selectedConversation!.id),
    enabled: Boolean(selectedConversation?.id),
    refetchInterval: 1500,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
  });
  const automationQuery = useQuery({
    queryKey: ["direct-customer-automation", workspaceId, selectedConversation?.id],
    queryFn: () => fetchDirectCustomerAutomation(selectedConversation!.id),
    enabled: Boolean(selectedConversation?.id),
    refetchInterval: 2000,
    refetchIntervalInBackground: true,
  });
  const orderEvidenceQuery = useQuery({
    queryKey: ["direct-order-evidence", workspaceId, selectedConversation?.id],
    queryFn: () => fetchDirectOrderEvidence(selectedConversation!.id),
    enabled: Boolean(workspaceId && selectedConversation?.id),
    staleTime: 60_000,
  });
  const confirmOrderEvidenceMutation = useMutation({
    mutationFn: () => confirmDirectOrderEvidence(
      selectedConversation!.id,
      Array.from(new Set((orderEvidenceQuery.data?.verified_orders ?? []).map((item) => item.order_id))),
    ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["direct-order-evidence", workspaceId, selectedConversation?.id] });
      void queryClient.invalidateQueries({ queryKey: ["direct-conversations", workspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["direct-customer-automation", workspaceId, selectedConversation?.id] });
    },
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
      prepareMutation.reset();
      void queryClient.invalidateQueries({ queryKey: ["direct-messages", workspaceId, selectedConversation?.id] });
      void queryClient.invalidateQueries({ queryKey: ["direct-conversations", workspaceId] });
    },
  });
  const profileMutation = useMutation({
    mutationFn: (conversationId: string) => refreshDirectParticipantProfile(conversationId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["direct-conversations", workspaceId] }),
  });
  const ensureLeadMutation = useMutation({
    mutationFn: (conversationId: string) => ensureDirectLead(conversationId),
    onSuccess: (_conversation, conversationId) => {
      void queryClient.invalidateQueries({ queryKey: ["direct-conversations", workspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["leads", workspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["direct-customer-automation", workspaceId, conversationId] });
    },
  });
  const ensureCustomerMutation = useMutation({
    mutationFn: (conversationId: string) => ensureDirectCustomer(conversationId),
    onSuccess: (_state, conversationId) => {
      void queryClient.invalidateQueries({ queryKey: ["direct-customer-automation", workspaceId, conversationId] });
      void queryClient.invalidateQueries({ queryKey: ["direct-conversations", workspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["customers", workspaceId] });
    },
  });
  const historyMutation = useMutation({
    mutationFn: () => startInstagramHistorySync(100, 20),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["instagram-history-sync", workspaceId] }),
  });
  const cancelHistoryMutation = useMutation({
    mutationFn: cancelInstagramHistorySync,
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
  const historyStopping = Boolean(historyActive && (historyQuery.data?.cancel_requested || cancelHistoryMutation.isPending || cancelHistoryMutation.data?.requested));
  const startHistory = () => { if (window.confirm(t("direct.historyStartConfirm"))) historyMutation.mutate(); };
  const stopHistory = () => { if (window.confirm(t("direct.historyStopConfirm"))) cancelHistoryMutation.mutate(); };

  useEffect(() => {
    setSelectedId(null);
    setReplyText("");
    profileRefreshAttempted.current.clear();
    readAttempted.current.clear();
    customerAutomationAttempted.current.clear();
  }, [workspaceId]);

  useEffect(() => {
    if (!conversationsQuery.data) return;
    const requestedId = requestedConversationId && conversationsQuery.data.some((item) => item.id === requestedConversationId)
      ? requestedConversationId
      : null;
    setSelectedId(requestedId);
  }, [conversationsQuery.data, requestedConversationId]);

  useEffect(() => {
    if (!isMobile || selectedId || listScrollPosition.current === 0) return;
    const frame = window.requestAnimationFrame(() => window.scrollTo(0, listScrollPosition.current));
    return () => window.cancelAnimationFrame(frame);
  }, [isMobile, selectedId]);

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
    const conversationId = selectedConversation?.id;
    if (!conversationId || !canManage) return;
    if (!orderIntentConversationIds.has(conversationId)) return;
    if (automationQuery.data?.stage !== "NOT_CREATED") return;
    if (customerAutomationAttempted.current.has(conversationId)) return;
    customerAutomationAttempted.current.add(conversationId);
    ensureCustomerMutation.mutate(conversationId);
  }, [automationQuery.data?.stage, canManage, ensureCustomerMutation, orderIntentConversationIds, selectedConversation?.id]);

  const lastComposerConversationId = useRef<string | null>(null);
  const { reset: clearPreparedReply } = prepareMutation;
  const { reset: clearSendState } = sendMutation;
  useEffect(() => {
    const id = selectedConversation?.id ?? null;
    if (lastComposerConversationId.current === id) return;
    lastComposerConversationId.current = id;
    setReplyText("");
    clearPreparedReply();
    clearSendState();
  }, [selectedConversation?.id, clearPreparedReply, clearSendState]);

  const historyStatus = historyQuery.data?.status;
  useEffect(() => {
    if (!historyStatus || !["COMPLETED", "PARTIAL"].includes(historyStatus)) return;
    queryClient.invalidateQueries({ queryKey: ["direct-conversations", workspaceId] });
    if (selectedConversation?.id) {
      queryClient.invalidateQueries({ queryKey: ["direct-messages", workspaceId, selectedConversation.id] });
    }
  }, [historyStatus, queryClient, selectedConversation?.id, workspaceId]);

  const safeSelectedConversationId = () => {
    const conversationId = selectedConversation?.id;
    if (!conversationId) return null;
    if (selectionTargetRef.current && selectionTargetRef.current !== conversationId) return null;
    return conversationId;
  };

  const handleSelectConversation = (conversationId: string) => {
    selectionTargetRef.current = conversationId;
    if (isMobile) {
      listScrollPosition.current = window.scrollY;
      window.scrollTo(0, 0);
    }
    setSelectedId(conversationId);
    router.push(`/direct?conversation=${encodeURIComponent(conversationId)}`, { scroll: false });
  };
  const handleBackToInbox = () => {
    selectionTargetRef.current = null;
    setSelectedId(null);
    setAiPanelOpen(false);
    router.replace("/direct", { scroll: false });
  };
  const threadOpenOnMobile = Boolean(selectedId);

  useEffect(() => {
    // Treat an open conversation like a full-screen mobile messenger:
    // global quick navigation remains accessible from the inbox and topbar.
    document.body.classList.toggle("direct-thread-open", isMobile && threadOpenOnMobile);
    return () => document.body.classList.remove("direct-thread-open");
  }, [isMobile, threadOpenOnMobile]);

  return (
    <WorkspacePage className={threadOpenOnMobile ? "min-h-full !px-3 !py-2 lg:!px-6 lg:!py-4" : "min-h-full"}>
      <div className={threadOpenOnMobile ? "hidden lg:block" : ""}>
      <WorkspaceHeader
        title={t("direct.title")}
        description={t("direct.description")}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setAiPanelOpen(true)}
              className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-border-subtle bg-surface-1 px-3 text-sm font-medium text-text-secondary transition hover:bg-surface-hover lg:hidden"
            ><Sparkles className="h-4 w-4" aria-hidden="true" /> {t("direct.aiQuick")}</button>
            <button
              type="button"
              aria-expanded={historyPanelOpen}
              onClick={() => setHistoryPanelOpen((value) => !value)}
              className={`inline-flex min-h-11 items-center gap-2 rounded-xl border px-3 text-sm font-medium transition hover:bg-surface-hover ${historyPanelOpen ? "border-primary/40 bg-primary/10 text-primary" : "border-border-subtle bg-surface-1 text-text-secondary"}`}
            ><Clock3 className="h-4 w-4" aria-hidden="true" /> {t("direct.history")}</button>
            <button
              type="button"
              onClick={() => void conversationsQuery.refetch()}
              disabled={conversationsQuery.isFetching}
              title={t("direct.refreshList")}
              aria-label={t("direct.refreshList")}
              className="grid min-h-11 min-w-11 place-items-center rounded-xl border border-border-subtle bg-surface-1 text-text-secondary transition hover:bg-surface-hover disabled:opacity-60"
            ><RefreshCw className={`h-4 w-4 ${conversationsQuery.isFetching ? "animate-spin" : ""}`} aria-hidden="true" /></button>
          </div>
        }
      />
      {(historyPanelOpen || historyActive) ? (
        <section className="grid min-w-0 gap-3 rounded-2xl border border-border-subtle bg-surface-1 p-3 sm:p-4" aria-label={t("direct.historyHeading")}>
          {historyPanelOpen ? (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0 flex-1">
                <h2 className="text-sm font-semibold text-text-primary">{t("direct.historyHeading")}</h2>
                <p className="mt-1 text-xs text-text-muted">{t("direct.historyHint")}</p>
                <p className="mt-1 text-xs text-text-muted">{t("direct.historyLimit")}</p>
              </div>
              {canManage && !historyActive ? (
                <Button variant="secondary" onClick={startHistory} disabled={historyMutation.isPending || statusQuery.data?.status !== "CONNECTED"}>
                  <RefreshCw className="h-4 w-4" />{t("direct.historyStart")}
                </Button>
              ) : null}
            </div>
          ) : null}
          <HistorySyncBanner sync={historyQuery.data} loading={historyQuery.isLoading} />
          {historyActive && canManage ? (
            <button type="button" onClick={stopHistory} disabled={historyStopping} className="inline-flex min-h-11 w-fit items-center gap-2 rounded-xl border border-danger/30 px-3 text-sm font-medium text-danger transition hover:bg-[var(--danger-surface)] disabled:opacity-60">
              <Square className="h-3.5 w-3.5" aria-hidden="true" />{historyStopping ? t("direct.historyStopping") : t("direct.historyStop")}
            </button>
          ) : null}
          {historyMutation.isError ? <p role="alert" className="text-sm text-danger">{t("direct.historyStartError")}</p> : null}
          {cancelHistoryMutation.isError ? <p role="alert" className="text-sm text-danger">{t("direct.historyStopError")}</p> : null}
        </section>
      ) : null}
      </div>

      <section
        className="grid min-w-0 gap-4 lg:min-h-[calc(100dvh-var(--topbar-height,72px)-190px)] lg:grid-cols-[minmax(260px,320px)_minmax(0,1fr)_minmax(320px,380px)]"
        data-direct-shell-content
      >
        <div className={threadOpenOnMobile ? "hidden min-w-0 lg:block" : "min-w-0"}>
        <ConversationList
          key={workspaceId}
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
        </div>
        <div className={threadOpenOnMobile ? "min-w-0" : "hidden min-w-0 lg:block"}>
        <MessageThread
          onBack={handleBackToInbox}
          onOpenAiPanel={() => setAiPanelOpen(true)}
          conversation={selectedConversation}
          automation={automationQuery.data}
          orderEvidence={orderEvidenceQuery.data}
          orderEvidenceLoading={orderEvidenceQuery.isLoading}
          orderEvidenceError={orderEvidenceQuery.isError}
          orderEvidenceConfirming={confirmOrderEvidenceMutation.isPending}
          orderEvidenceConfirmError={confirmOrderEvidenceMutation.isError}
          onConfirmOrderEvidence={() => {
            if (!safeSelectedConversationId()) return;
            const count = orderEvidenceQuery.data?.verified_orders.length ?? 0;
            if (!count || !window.confirm(`Зберегти точні зв’язки з ${count} відправленнями? Замовлення, ціни, оплата й товари не зміняться.`)) return;
            confirmOrderEvidenceMutation.mutate();
          }}
          automationLoading={automationQuery.isLoading}
          automationError={automationQuery.isError || ensureCustomerMutation.isError}
          canManage={canManage}
          ensuringCustomer={ensureCustomerMutation.isPending}
          onEnsureCustomer={() => {
            const conversationId = safeSelectedConversationId();
            if (conversationId) ensureCustomerMutation.mutate(conversationId);
          }}
          ensuringLead={ensureLeadMutation.isPending}
          leadError={ensureLeadMutation.isError}
          onEnsureLead={() => {
            const conversationId = safeSelectedConversationId();
            if (conversationId) ensureLeadMutation.mutate(conversationId);
          }}
          loading={messagesQuery.isLoading}
          error={messagesQuery.isError}
          messages={messagesQuery.data ?? []}
          replyText={replyText}
          setReplyText={(value) => {
            setReplyText(value);
            prepareMutation.reset();
            sendMutation.reset();
          }}
          onPrepare={() => prepareMutation.mutate()}
          onSend={() => sendMutation.mutate()}
          preparePending={prepareMutation.isPending}
          prepareError={prepareMutation.isError}
          sendError={sendMutation.isError}
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
        </div>
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
  const { t } = useI18n();
  if (loading || !sync) return null;
  const active = ACTIVE_HISTORY_STATUSES.has(sync.status);
  const statusLabels: Record<string, string> = {
    PENDING: t("direct.historyPending"),
    RUNNING: t("direct.historyRunning"),
    RETRY_PENDING: t("direct.historyRetry"),
    COMPLETED: t("direct.historyCompleted"),
    PARTIAL: t("direct.historyPartial"),
    CANCELLED: t("direct.historyCancelled"),
    FAILED_SAFE: t("direct.historyFailed"),
  };
  const stopping = active && sync.cancel_requested;
  const progress = Math.min(100, Math.round(100 * sync.conversations_discovered / Math.max(sync.conversation_limit, 1)));
  return (
    <div className="grid min-w-0 gap-2" data-direct-history-progress>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-text-primary">{stopping ? t("direct.historyStopping") : statusLabels[sync.status] ?? sync.status}</p>
        <span className={`rounded-full px-2 py-1 text-xs font-medium ${active ? "bg-primary/10 text-primary" : sync.status === "FAILED_SAFE" ? "bg-[var(--danger-surface)] text-danger" : "bg-surface-2 text-text-secondary"}`}>{progress}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-3" role="progressbar" aria-valuenow={sync.conversations_discovered} aria-valuemin={0} aria-valuemax={sync.conversation_limit} aria-label={t("direct.historyProgress")}>
        <div className="h-full rounded-full bg-primary transition-[width] duration-300 motion-reduce:transition-none" style={{ width: `${progress}%` }} />
      </div>
      <p className="text-xs text-text-muted">{t("direct.historyProgress")}: {sync.conversations_discovered}/{sync.conversation_limit} · {t("direct.historyNew")}: {sync.messages_imported} · {t("direct.historyExisting")}: {sync.messages_existing}</p>
      {sync.messages_unavailable > 0 || sync.error_count > 0 ? <p className="text-xs text-warning">{t("direct.historyUnavailable")}: {sync.messages_unavailable} · {t("direct.historyErrors")}: {sync.error_count}</p> : null}
    </div>
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

const DIRECT_INBOX_BATCH_SIZE = 20;

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
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"all" | "unread" | "orders">("all");
  const [visibleCount, setVisibleCount] = useState(DIRECT_INBOX_BATCH_SIZE);
  const loadMoreRef = useRef<HTMLDivElement>(null);

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
  const filteredConversations = useMemo(() => {
    const term = search.trim().toLocaleLowerCase();
    return orderedConversations.filter((item) => {
      if (filter === "unread" && item.unread_count === 0) return false;
      if (filter === "orders" && !orderIntentConversationIds.has(item.id) && !item.linked_order_id) return false;
      if (!term) return true;
      return [item.participant_display_name, item.participant_username, item.participant_scoped_id]
        .some((value) => value?.toLocaleLowerCase().includes(term));
    });
  }, [filter, orderedConversations, orderIntentConversationIds, search]);
  const shown = filteredConversations.slice(0, visibleCount);
  const hasMore = shown.length < filteredConversations.length;

  useEffect(() => {
    if (!hasMore || !loadMoreRef.current || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setVisibleCount((count) => Math.min(count + DIRECT_INBOX_BATCH_SIZE, filteredConversations.length));
      },
      { rootMargin: "240px 0px", threshold: 0 },
    );
    observer.observe(loadMoreRef.current);
    return () => observer.disconnect();
  }, [filteredConversations.length, hasMore, visibleCount]);

  if (loading) return <aside className="rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-3"><LoadingSkeleton /></aside>;
  if (error) return <aside className="rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-3"><ErrorState title="Не вдалося завантажити Direct" description="Оновіть сторінку або перевірте workspace." /></aside>;
  return (
    <aside className="min-w-0 rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-3 shadow-[var(--shadow-card)]" data-direct-progressive-list>
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="font-black">Діалоги <span className="text-sm font-medium text-text-muted">({conversations.length})</span></h2>
        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-black ${liveError ? "bg-rose-500/15 text-rose-600" : isLive ? "bg-emerald-500/15 text-emerald-600" : "bg-amber-500/15 text-amber-600"}`}>
          {liveError ? <WifiOff className="h-3 w-3" /> : <Wifi className="h-3 w-3" />}
          {liveError ? "Offline" : isLive ? "Live" : "…"}
        </span>
      </div>
      <input
        type="search"
        aria-label="Пошук діалогів"
        className="mb-3 min-h-11 w-full rounded-xl border border-border-subtle bg-surface-2 px-3 text-sm"
        placeholder="Імʼя або Instagram username"
        value={search}
        onChange={(event) => { setSearch(event.target.value); setVisibleCount(DIRECT_INBOX_BATCH_SIZE); }}
      />
      <div className="mb-3 flex gap-2 overflow-x-auto pb-1" aria-label="Фільтр діалогів">
        {([
          ["all", "Усі"],
          ["unread", "Непрочитані"],
          ["orders", "Замовлення"],
        ] as const).map(([key, label]) => (
          <button
            key={key}
            type="button"
            aria-pressed={filter === key}
            onClick={() => { setFilter(key); setVisibleCount(DIRECT_INBOX_BATCH_SIZE); }}
            className={`min-h-9 shrink-0 rounded-full border px-3 text-xs font-bold transition ${filter === key ? "border-primary bg-primary/15 text-primary" : "border-border-subtle bg-surface-2 text-text-secondary"}`}
          >{label}</button>
        ))}
      </div>
      {filteredConversations.length === 0
        ? (conversations.length === 0
          ? <DirectEmptyState instagramStatus={instagramStatus} />
          : <p className="rounded-xl bg-surface-2 p-4 text-sm text-text-muted">За цим запитом діалогів немає.</p>)
        : (
          <div className="space-y-1.5" role="list">
            {shown.map((item) => {
              const orderIntent = orderIntentConversationIds.has(item.id);
              return (
                <button
                  role="listitem"
                  type="button"
                  key={item.id}
                  onClick={() => onSelect(item.id)}
                  aria-current={selectedId === item.id ? "true" : undefined}
                  className={`w-full rounded-xl border px-3 py-2.5 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring ${selectedId === item.id ? "border-primary bg-primary/10" : "border-transparent bg-surface-2 hover:border-border-strong"}`}
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <ParticipantAvatar conversation={item} size="sm" />
                    <div className="min-w-0 flex-1">
                      <div className="flex min-w-0 items-center gap-2">
                        <h3 className="min-w-0 flex-1 truncate text-sm font-bold text-text-primary">{item.participant_display_name ?? item.participant_username ?? "Клієнт Instagram"}</h3>
                        {item.participant_is_verified_user ? <BadgeCheck className="h-4 w-4 shrink-0 text-sky-500" /> : null}
                        {item.unread_count > 0 ? <span className="shrink-0 rounded-full bg-primary px-2 py-0.5 text-xs font-black text-white">{item.unread_count}</span> : null}
                      </div>
                      <p className="mt-0.5 truncate text-xs text-text-muted">{item.participant_username ? `@${item.participant_username}` : item.participant_scoped_id ?? "Instagram Direct"}</p>
                      {orderIntent || item.linked_order_id || item.linked_customer_id ? (
                        <p className="mt-1 truncate text-[11px] font-semibold text-primary">
                          {item.linked_order_id ? "Замовлення оформлено" : orderIntent ? "Ймовірне замовлення" : "Потенційний клієнт"}
                        </p>
                      ) : null}
                    </div>
                  </div>
                </button>
              );
            })}
            {hasMore ? (
              <>
                <div ref={loadMoreRef} className="h-px" aria-hidden="true" data-direct-load-sentinel />
                <button type="button" className="min-h-11 w-full rounded-xl border border-border-subtle bg-surface-2 text-sm font-semibold text-primary" onClick={() => setVisibleCount((count) => count + DIRECT_INBOX_BATCH_SIZE)}>
                  Завантажити ще
                </button>
              </>
            ) : null}
            <p className="pt-2 text-center text-xs text-text-muted" aria-live="polite">Показано {shown.length} із {filteredConversations.length}</p>
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
  automation,
  orderEvidence,
  orderEvidenceLoading,
  orderEvidenceError,
  orderEvidenceConfirming,
  orderEvidenceConfirmError,
  onConfirmOrderEvidence,
  automationLoading,
  automationError,
  canManage,
  ensuringCustomer,
  onEnsureCustomer,
  ensuringLead,
  leadError,
  onEnsureLead,
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
  preparePending,
  prepareError,
  sendError,
  onBack,
  onOpenAiPanel,
}: {
  onBack: () => void;
  onOpenAiPanel: () => void;
  conversation?: DirectConversation | null;
  automation?: DirectCustomerAutomationState;
  orderEvidence?: DirectOrderEvidence;
  orderEvidenceLoading: boolean;
  orderEvidenceError: boolean;
  orderEvidenceConfirming: boolean;
  orderEvidenceConfirmError: boolean;
  onConfirmOrderEvidence: () => void;
  automationLoading: boolean;
  automationError: boolean;
  canManage: boolean;
  ensuringCustomer: boolean;
  onEnsureCustomer: () => void;
  ensuringLead: boolean;
  leadError: boolean;
  onEnsureLead: () => void;
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
  preparePending: boolean;
  prepareError: boolean;
  sendError: boolean;
}) {
  const scrollContainer = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textarea = composerRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 112)}px`;
  }, [replyText]);

  useEffect(() => {
    const element = scrollContainer.current;
    if (!element) return;
    element.scrollTo({ top: element.scrollHeight, behavior: messages.length > 1 ? "smooth" : "auto" });
  }, [conversation?.id, messages.length]);

  if (!conversation) return <section className="rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-4"><EmptyState title="Оберіть діалог" description="Повідомлення та AI-підказки зʼявляться після вибору розмови." /></section>;
  return (
    <section className="direct-mobile-thread flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 shadow-[var(--shadow-card)] lg:min-h-[520px]" data-direct-mobile-thread>
      <header className="flex shrink-0 items-center gap-2 border-b border-border-subtle px-2 py-2 lg:hidden">
        <button type="button" onClick={onBack} aria-label="Назад до діалогів" className="flex min-h-11 shrink-0 items-center gap-1 rounded-xl px-2 text-sm font-bold text-primary">
          <ArrowLeft className="h-5 w-5" /> Назад
        </button>
        <ParticipantAvatar conversation={conversation} size="sm" />
        <div className="min-w-0 flex-1 leading-tight">
          <p className="truncate text-sm font-black text-text-primary">{conversation.participant_display_name ?? "Клієнт Instagram"}</p>
          <p className="truncate text-xs text-text-muted">{conversation.participant_username ? `@${conversation.participant_username}` : "Instagram Direct"}</p>
        </div>
        <button type="button" className="min-h-11 shrink-0 rounded-xl px-2 text-xs font-bold text-primary" onClick={onOpenAiPanel}>AI</button>
      </header>
      <div className="hidden lg:block">
        <ParticipantProfileCard conversation={conversation} onRefresh={onRefreshProfile} refreshing={profileRefreshing} />
        <DirectLeadCard conversation={conversation} canManage={canManage} ensuring={ensuringLead} error={leadError} onEnsure={onEnsureLead} />
        <CustomerAutomationCard
        conversation={conversation}
        automation={automation}
        existingOrdersCount={orderEvidence?.verified_orders.length ?? 0}
        evidenceReady={!orderEvidenceLoading && !orderEvidenceError && !orderEvidence?.scan_truncated}
        loading={automationLoading}
        error={automationError}
        canManage={canManage}
        ensuring={ensuringCustomer}
        onEnsure={onEnsureCustomer}
        />
        <DirectOrderEvidenceCard evidence={orderEvidence} loading={orderEvidenceLoading} error={orderEvidenceError} canManage={canManage} confirming={orderEvidenceConfirming} confirmError={orderEvidenceConfirmError} onConfirm={onConfirmOrderEvidence} />
      </div>
      <details className="shrink-0 border-b border-border-subtle lg:hidden" data-direct-mobile-details>
        <summary className="cursor-pointer px-4 py-2 text-xs font-bold text-text-secondary">Деталі клієнта та замовлення</summary>
        <div className="max-h-[35dvh] overflow-y-auto">
          <ParticipantProfileCard conversation={conversation} onRefresh={onRefreshProfile} refreshing={profileRefreshing} />
          <DirectLeadCard conversation={conversation} canManage={canManage} ensuring={ensuringLead} error={leadError} onEnsure={onEnsureLead} />
          <CustomerAutomationCard conversation={conversation} automation={automation} existingOrdersCount={orderEvidence?.verified_orders.length ?? 0} evidenceReady={!orderEvidenceLoading && !orderEvidenceError && !orderEvidence?.scan_truncated} loading={automationLoading} error={automationError} canManage={canManage} ensuring={ensuringCustomer} onEnsure={onEnsureCustomer} />
          <DirectOrderEvidenceCard evidence={orderEvidence} loading={orderEvidenceLoading} error={orderEvidenceError} canManage={canManage} confirming={orderEvidenceConfirming} confirmError={orderEvidenceConfirmError} onConfirm={onConfirmOrderEvidence} />
        </div>
      </details>
      <div ref={scrollContainer} className="sellora-scrollbar min-h-0 flex-1 space-y-3 overflow-y-auto p-3 lg:p-4" data-direct-live-thread>
        {loading ? <LoadingSkeleton /> : null}
        {error ? <ErrorState title="Не вдалося завантажити повідомлення" description="Спробуйте оновити діалог." /> : null}
        {!loading && !error && messages.length === 0 ? <EmptyState title="Повідомлень ще немає" description="Нові Instagram webhooks або імпортована історія зʼявляться тут." /> : null}
        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.direction === "OUTBOUND" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[88%] rounded-2xl px-3 py-2.5 text-sm leading-relaxed sm:max-w-[82%] lg:px-4 lg:py-3 ${message.direction === "OUTBOUND" ? "rounded-br-md bg-primary/15 text-text-primary" : "rounded-bl-md bg-surface-2 text-text-primary"}`}>
              <p className="whitespace-pre-wrap break-words">{message.text}</p>
              <div className={`mt-1 flex flex-wrap items-center gap-1.5 text-[10px] leading-4 text-text-muted ${message.direction === "OUTBOUND" ? "justify-end" : ""}`}>
                <time dateTime={message.received_at}>{formatDirectMessageTime(message.received_at)}</time>
                {message.direction === "OUTBOUND" ? <span aria-label={messageStatusLabel(message)}>· {messageStatusLabel(message)}</span> : null}
                {message.edit_count ? <span>· ред.</span> : null}
                {message.reaction ? <span className="rounded-full bg-surface-1 px-1.5">{message.reaction}</span> : null}
              </div>
            </div>
          </div>
        ))}
      </div>
      <footer className="shrink-0 border-t border-border-subtle bg-surface-1 px-2.5 pb-2 pt-2.5 lg:p-3" data-direct-compact-composer>
        <div className="flex min-w-0 items-end gap-1.5 rounded-[20px] border border-border-subtle bg-surface-2 p-1.5 transition-colors focus-within:border-primary/70 focus-within:ring-1 focus-within:ring-primary/20">
          <label className="sr-only" htmlFor="direct-message-reply">Повідомлення клієнту</label>
          <textarea
            id="direct-message-reply"
            ref={composerRef}
            rows={1}
            value={replyText}
            onChange={(event) => setReplyText(event.target.value)}
            className="min-h-11 max-h-28 min-w-0 flex-1 resize-none overflow-y-auto border-0 bg-transparent px-2.5 py-2.5 text-base leading-6 text-text-primary outline-none placeholder:text-text-muted"
            placeholder="Написати повідомлення…"
            aria-label="Відповідь менеджера"
            data-direct-reply-input
          />
          <button
            type="button"
            aria-label="Надіслати повідомлення"
            title="Надіслати вручну"
            disabled={sendDisabled || !replyText.trim() || sendPending}
            onClick={onSend}
            className="grid h-11 w-11 min-h-11 min-w-11 shrink-0 place-items-center rounded-2xl bg-primary text-primary-foreground shadow-sm transition hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring disabled:cursor-not-allowed disabled:opacity-40"
            data-direct-send
          >
            {sendPending ? <RefreshCw className="h-5 w-5 animate-spin" aria-hidden="true" /> : <Send className="h-5 w-5" aria-hidden="true" />}
          </button>
        </div>
        <div className="mt-1.5 flex min-w-0 items-center justify-between gap-2 px-1">
          <span className="inline-flex min-w-0 items-center gap-1 text-[11px] font-medium text-text-muted" title={noAutoSend}>
            <ShieldCheck className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span className="truncate">AI-чернетки · лише вручну</span>
          </span>
          <button
            type="button"
            onClick={onPrepare}
            disabled={!replyText.trim() || preparePending || sendPending}
            className="inline-flex min-h-9 shrink-0 items-center gap-1 rounded-xl px-2.5 text-xs font-semibold text-primary transition hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring disabled:cursor-not-allowed disabled:opacity-40"
            data-direct-prepare
          >
            {preparePending ? <RefreshCw className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />}
            Перевірити
          </button>
        </div>
        {prepareResult ? (
          <p className={`mt-1 rounded-lg px-2 py-1.5 text-xs font-medium ${prepareResult.ready ? "bg-emerald-500/10 text-emerald-600" : "bg-rose-500/10 text-rose-600"}`} role="status">
            {prepareResult.ready ? "Можна надсилати після ручного підтвердження." : `Відправлення заблоковано: ${prepareResult.blockers.join(", ")}`}
          </p>
        ) : null}
        {prepareError ? <p className="mt-1 text-xs text-danger" role="alert">Не вдалося перевірити відправлення. Спробуйте пізніше.</p> : null}
        {sendError ? <p className="mt-1 text-xs text-danger" role="alert">Не вдалося підтвердити надсилання. Перевірте переписку перед повторною спробою.</p> : null}
      </footer>
    </section>
  );
}

function DirectLeadCard({
  conversation, canManage, ensuring, error, onEnsure,
}: {
  conversation: DirectConversation;
  canManage: boolean;
  ensuring: boolean;
  error: boolean;
  onEnsure: () => void;
}) {
  if (conversation.channel !== "INSTAGRAM") return null;
  const linked = Boolean(conversation.linked_lead_id);
  const actionable = canManage && !linked && conversation.status !== "SPAM" && conversation.status !== "ARCHIVED";
  return (
    <section className="border-b border-border-subtle bg-surface-2/40 px-4 py-3" data-direct-lead>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-black text-text-primary">Заявка на продаж</p>
            <span className={`rounded-full px-2 py-1 text-xs font-bold ${linked ? "bg-emerald-500/15 text-emerald-700" : "bg-surface-1 text-text-muted"}`}>
              {linked ? "Лід прив’язано" : "Без ліда"}
            </span>
          </div>
          <p className="mt-1 text-xs text-text-secondary">
            {linked
              ? "Інтерес покупця збережено як лід. Це не підтвердження покупки."
              : "Створіть лід для звернення покупця. Клієнт, замовлення й відправлення не створюються автоматично."}
          </p>
          {error ? <p className="mt-1 text-xs font-semibold text-rose-600" role="alert" data-direct-lead-error>Не вдалося створити лід. Перевірте, чи є вхідне повідомлення, і повторіть спробу.</p> : null}
        </div>
        {linked ? (
          <Link className="inline-flex min-h-10 items-center rounded-2xl border border-border-subtle bg-surface-1 px-4 py-2 text-sm font-bold text-primary" href="/leads">
            Перейти до лідів
          </Link>
        ) : actionable ? (
          <Button variant="secondary" onClick={onEnsure} disabled={ensuring} data-direct-lead-action>
            {ensuring ? <RefreshCw className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
            {ensuring ? "Створення…" : "Створити лід"}
          </Button>
        ) : null}
      </div>
    </section>
  );
}


function CustomerAutomationCard({
  conversation,
  automation,
  existingOrdersCount,
  evidenceReady,
  loading,
  error,
  canManage,
  ensuring,
  onEnsure,
}: {
  conversation: DirectConversation;
  automation?: DirectCustomerAutomationState;
  existingOrdersCount: number;
  evidenceReady: boolean;
  loading: boolean;
  error: boolean;
  canManage: boolean;
  ensuring: boolean;
  onEnsure: () => void;
}) {
  const customer = automation?.customer;
  const missingLabels: Record<string, string> = {
    name: "ПІБ",
    phone: "телефон",
    city: "місто",
    delivery_address: "відділення Нової пошти",
  };
  if (loading) return <div className="border-b border-border-subtle px-4 py-3"><LoadingSkeleton rows={1} /></div>;
  return (
    <section className="border-b border-border-subtle bg-surface-2/60 px-4 py-3" data-direct-customer-automation>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-black">Клієнт і замовлення</p>
            <span className={`rounded-full px-2 py-1 text-xs font-black ${automation?.profile_complete ? "bg-emerald-500/15 text-emerald-700" : customer ? "bg-amber-500/15 text-amber-700" : "bg-surface-1 text-text-muted"}`}>
              {automation?.profile_complete ? "Профіль заповнено" : customer ? "Потенційний клієнт" : "Не створено"}
            </span>
          </div>
          {customer ? (
            <p className="mt-1 text-sm text-text-secondary">
              {customer.name}{customer.instagram_username ? ` · @${customer.instagram_username}` : ""}
            </p>
          ) : (
            <p className="mt-1 text-sm text-text-secondary">Sellora створить prospect без телефону, а повні дані збере під час оформлення.</p>
          )}
          {automation?.missing_fields.length ? (
            <p className="mt-1 text-xs font-semibold text-amber-700">Потрібно доповнити: {automation.missing_fields.map((field) => missingLabels[field] ?? field).join(", ")}.</p>
          ) : null}
          {error ? <p className="mt-1 text-xs font-semibold text-rose-600">Не вдалося оновити зв’язок із клієнтом. Повторіть дію.</p> : null}
        </div>
        <div className="flex flex-wrap gap-2">
          {!customer && canManage ? (
            <Button variant="secondary" onClick={onEnsure} disabled={ensuring}>
              {ensuring ? <RefreshCw className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
              Створити prospect
            </Button>
          ) : null}
          {customer && evidenceReady && canManage ? (
            <Link
              className="inline-flex min-h-10 items-center gap-2 rounded-2xl bg-primary px-4 py-2 text-sm font-black text-primary-foreground"
              href={`/orders?create=1&customer_id=${encodeURIComponent(customer.id)}&direct_conversation_id=${encodeURIComponent(conversation.id)}`}
            >
              <ShoppingBag className="h-4 w-4" />
              {existingOrdersCount > 0 || automation?.linked_order_id ? "Створити нове замовлення" : "Оформити замовлення"}
            </Link>
          ) : null}
          {automation?.linked_order_id ? (
            <Link
              className="inline-flex min-h-10 items-center gap-2 rounded-2xl border border-border-subtle bg-surface-1 px-4 py-2 text-sm font-black text-primary"
              href={`/orders?order_id=${encodeURIComponent(automation.linked_order_id)}`}
            >
              <CheckCircle2 className="h-4 w-4" />
              Відкрити замовлення
            </Link>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function formatDirectMessageTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? ""
    : new Intl.DateTimeFormat("uk-UA", { hour: "2-digit", minute: "2-digit" }).format(date);
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