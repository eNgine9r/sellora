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
  UserPlus,
  UserRound,
  Users,
  Wifi,
  WifiOff,
  ArrowLeft,
} from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { Button, WorkspaceHeader, WorkspacePage } from "@/components/crm-workspace";
import { useDirectLive } from "@/components/direct-live-provider";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";
import { Drawer } from "@/components/ui/overlay";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { fetchAISuggestions } from "@/services/ai";
import {
  ensureDirectCustomer,
  fetchDirectConversations,
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
  DirectCustomerAutomationState,
  DirectMessage,
  InstagramHistorySync,
} from "@/types/direct";

const ACTIVE_HISTORY_STATUSES = new Set(["PENDING", "RUNNING", "RETRY_PENDING"]);

export default function DirectPage() {
  const { t } = useI18n();
  const { currentWorkspace } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { isLive, isError: liveError, orderIntentConversationIds } = useDirectLive();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  type Draft = { text: string; revision: number };
  type ReplyContext = { workspaceId: string; conversationId: string; key: string; text: string; revision: number };
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [outcomes, setOutcomes] = useState<Record<string, string>>({});
  const [preparations, setPreparations] = useState<Record<string, { revision: number; result?: PrepareResult; error?: boolean }>>({});
  const profileRefreshAttempted = useRef(new Set<string>());
  const readAttempted = useRef(new Set<string>());
  const customerAutomationAttempted = useRef(new Set<string>());

  const workspaceId = currentWorkspace?.workspace_id;
  const canManage = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";
  const conversationsQuery = useQuery({
    queryKey: ["direct-conversations", workspaceId],
    queryFn: fetchDirectConversations,
    enabled: Boolean(workspaceId),
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });
  const selectedConversation = useMemo(
    () => conversationsQuery.data?.find((item) => item.id === selectedId),
    [conversationsQuery.data, selectedId],
  );
  const messagesQuery = useQuery({
    queryKey: ["direct-messages", workspaceId, selectedConversation?.id],
    queryFn: () => fetchDirectMessages(selectedConversation!.id),
    enabled: Boolean(selectedConversation?.id),
    refetchInterval: 4000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });
  const automationQuery = useQuery({
    queryKey: ["direct-customer-automation", workspaceId, selectedConversation?.id],
    queryFn: () => fetchDirectCustomerAutomation(selectedConversation!.id),
    enabled: Boolean(selectedConversation?.id),
    refetchInterval: (query) => query.state.data?.stage === "NOT_CREATED" && canManage ? 5000 : false,
    refetchIntervalInBackground: false,
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

  const draftKey = `${workspaceId ?? ""}:${selectedConversation?.id ?? ""}`;
  const draft = drafts[draftKey] ?? { text: "", revision: 0 };
  const replyText = draft.text;
  const outcome = outcomes[draftKey];
  const preparation = preparations[draftKey];
  const replyContext = (): ReplyContext | null => workspaceId && selectedConversation && canManage
    ? { workspaceId, conversationId: selectedConversation.id, key: draftKey, text: draft.text, revision: draft.revision }
    : null;
  const setReplyText = (text: string) => {
    if (!canManage || !selectedConversation) return;
    setDrafts((current) => ({ ...current, [draftKey]: { text, revision: (current[draftKey]?.revision ?? 0) + 1 } }));
    setOutcomes((current) => {
      if (!["SENT", "FAILED_SAFE"].includes(current[draftKey])) return current;
      const next = { ...current }; delete next[draftKey]; return next;
    });
  };
  const analysisMutation = useMutation({
    mutationFn: ({ conversationId }: ReplyContext) => runDirectAnalysis(conversationId),
    onSuccess: (_result, variables) => queryClient.invalidateQueries({ queryKey: ["ai-suggestions", variables.workspaceId, variables.conversationId] }),
  });
  const prepareMutation = useMutation({
    mutationFn: (variables: ReplyContext) => prepareDirectReply(variables.conversationId, variables.text),
    onSuccess: (result, variables) => setPreparations((current) => ({ ...current, [variables.key]: { revision: variables.revision, result } })),
    onError: (_error, variables) => setPreparations((current) => ({ ...current, [variables.key]: { revision: variables.revision, error: true } })),
  });
  const sendMutation = useMutation({
    mutationFn: (variables: ReplyContext) => sendDirectReply(variables.conversationId, variables.text, crypto.randomUUID()),
    onMutate: (variables) => setOutcomes((current) => ({ ...current, [variables.key]: "SENDING" })),
    onSuccess: (result, variables) => {
      setOutcomes((current) => ({ ...current, [variables.key]: result.status }));
      if (result.status === "SENT") {
        setDrafts((current) => {
          if ((current[variables.key]?.revision ?? 0) !== variables.revision) return current;
          return { ...current, [variables.key]: { text: "", revision: variables.revision + 1 } };
        });
      }
      void queryClient.invalidateQueries({ queryKey: ["direct-messages", variables.workspaceId, variables.conversationId] });
      void queryClient.invalidateQueries({ queryKey: ["direct-conversations", variables.workspaceId] });
    },
    // A lost response can follow provider acceptance. Never offer a blind retry.
    onError: (_error, variables) => setOutcomes((current) => ({ ...current, [variables.key]: "UNKNOWN" })),
  });
  const profileMutation = useMutation({
    mutationFn: (conversationId: string) => refreshDirectParticipantProfile(conversationId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["direct-conversations", workspaceId] }),
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
    setAiPanelOpen(false);
    profileRefreshAttempted.current.clear();
    readAttempted.current.clear();
    customerAutomationAttempted.current.clear();
  }, [workspaceId]);

  useEffect(() => {
    const requestedId = searchParams.get("conversation");
    setSelectedId(requestedId && conversationsQuery.data?.some((item) => item.id === requestedId) ? requestedId : null);
  }, [conversationsQuery.data, searchParams]);

  useEffect(() => {
    if (!canManage || !selectedConversation || selectedConversation.channel !== "INSTAGRAM") return;
    if (selectedConversation.participant_profile_status === "READY") return;
    if (profileRefreshAttempted.current.has(selectedConversation.id)) return;
    const retryAt = selectedConversation.participant_profile_next_retry_at
      ? new Date(selectedConversation.participant_profile_next_retry_at).getTime()
      : 0;
    if (retryAt > Date.now()) return;
    profileRefreshAttempted.current.add(selectedConversation.id);
    profileMutation.mutate(selectedConversation.id);
  }, [canManage, selectedConversation, profileMutation]);

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

  const historyStatus = historyQuery.data?.status;
  useEffect(() => {
    if (!historyStatus || !["COMPLETED", "PARTIAL"].includes(historyStatus)) return;
    queryClient.invalidateQueries({ queryKey: ["direct-conversations", workspaceId] });
    if (selectedConversation?.id) {
      queryClient.invalidateQueries({ queryKey: ["direct-messages", workspaceId, selectedConversation.id] });
    }
  }, [historyStatus, queryClient, selectedConversation?.id, workspaceId]);

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
              {liveError ? t("direct.liveUnavailable") : isLive ? t("direct.live") : t("direct.connecting")}
            </span>
            <Button
              variant="secondary"
              onClick={() => historyMutation.mutate()}
              disabled={!canManage || historyMutation.isPending || historyActive || statusQuery.data?.status !== "CONNECTED"}
            >
              <RefreshCw className={`h-4 w-4 ${historyMutation.isPending || historyActive ? "animate-spin" : ""}`} />
              {historyActive ? t("direct.syncActive") : t("direct.syncHistory")}
            </Button>
            <Button onClick={() => conversationsQuery.refetch()}>
              <RefreshCw className="h-4 w-4" />
              {t("direct.refresh")}
            </Button>
          </div>
        }
      />

      {historyMutation.isError || profileMutation.isError ? <p role="alert" className="text-sm text-rose-600">{t("direct.actionError")}</p> : null}
      <HistorySyncBanner sync={historyQuery.data} loading={historyQuery.isLoading} />

      <div className="min-[1440px]:hidden">
        <button
          type="button"
          disabled={!selectedConversation}
          onClick={() => setAiPanelOpen(true)}
          className="min-h-11 w-full rounded-2xl border border-border-subtle bg-surface-1 px-4 py-2 text-sm font-black text-primary shadow-[var(--shadow-card)]"
        >
          {t("direct.openAiPanel")}
        </button>
      </div>

      <section
        className="grid h-[max(540px,calc(100dvh-var(--topbar-height,72px)-240px))] min-w-0 gap-3 lg:grid-cols-[280px_minmax(0,1fr)] min-[1440px]:grid-cols-[280px_minmax(0,1fr)_300px]"
        data-direct-shell-content
      >
        <div className={`${selectedConversation ? "hidden lg:block" : "block"} min-h-0 overflow-hidden`}>
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
        </div>
        <div className={`${selectedConversation ? "flex" : "hidden lg:flex"} min-h-0 min-w-0 flex-col`}>
          {selectedConversation ? <Button variant="secondary" className="mb-2 lg:hidden" onClick={() => { setSelectedId(null); setAiPanelOpen(false); router.replace("/direct", { scroll: false }); }}><ArrowLeft className="h-4 w-4" />{t("direct.backToDialogs")}</Button> : null}
        <MessageThread
          conversation={selectedConversation}
          automation={automationQuery.data}
          automationLoading={automationQuery.isLoading}
          automationError={automationQuery.isError || ensureCustomerMutation.isError}
          canManage={canManage}
          ensuringCustomer={ensureCustomerMutation.isPending}
          onEnsureCustomer={() => selectedConversation && ensureCustomerMutation.mutate(selectedConversation.id)}
          loading={messagesQuery.isLoading}
          error={messagesQuery.isError}
          messages={messagesQuery.data ?? []}
          replyText={replyText}
          setReplyText={setReplyText}
          onPrepare={() => { const context = replyContext(); if (context) prepareMutation.mutate(context); }}
          onSend={() => { const context = replyContext(); if (context && !sendMutation.isPending && (!outcome || ["SENT", "FAILED_SAFE"].includes(outcome))) sendMutation.mutate(context); }}
          onRefreshProfile={() => selectedConversation && profileMutation.mutate(selectedConversation.id)}
          profileRefreshing={profileMutation.isPending}
          sendDisabled={
            !canManage
            || Boolean(outcome && !["SENT", "FAILED_SAFE"].includes(outcome))
            || !selectedConversation
            || selectedConversation.channel !== "INSTAGRAM"
            || statusQuery.data?.status !== "CONNECTED"
            || sendMutation.isPending
          }
          prepareResult={preparation?.revision === draft.revision ? preparation.result : undefined}
          prepareError={preparation?.revision === draft.revision && Boolean(preparation.error)}
          sendOutcome={outcome}
          sendPending={sendMutation.isPending}
          noAutoSend={t("direct.noAutoSend")}
        />
        </div>
        <div className="hidden min-h-0 overflow-y-auto min-[1440px]:block">
          <AiPanel
            loading={suggestionsQuery.isLoading}
            suggestions={suggestionsQuery.data ?? []}
            onAnalyze={() => { const context = replyContext(); if (context) analysisMutation.mutate(context); }}
            analyzing={analysisMutation.isPending || !canManage || !selectedConversation}
            analysisError={analysisMutation.isError && analysisMutation.variables?.key === draftKey}
            onUseDraft={(text) => setReplyText(text)}
            connectionStatus={statusQuery.data?.status ?? "DISCONNECTED"}
          />
        </div>
      </section>

      <Drawer open={aiPanelOpen} title={t("direct.aiPanel")} onClose={() => setAiPanelOpen(false)}>
        <AiPanel loading={suggestionsQuery.isLoading} suggestions={suggestionsQuery.data ?? []}
          onAnalyze={() => { const context = replyContext(); if (context) analysisMutation.mutate(context); }}
          analyzing={analysisMutation.isPending || !canManage || !selectedConversation}
          analysisError={analysisMutation.isError && analysisMutation.variables?.key === draftKey}
          onUseDraft={(text) => setReplyText(text)} connectionStatus={statusQuery.data?.status ?? "DISCONNECTED"} embedded />
      </Drawer>
    </WorkspacePage>
  );
}

function HistorySyncBanner({ sync, loading }: { sync?: InstagramHistorySync | null; loading: boolean }) {
  const { t } = useI18n();
  if (loading || !sync) return null;
  const active = ACTIVE_HISTORY_STATUSES.has(sync.status);
  const statusLabel: Record<string, string> = {
    PENDING: t("direct.historyPending"),
    RUNNING: t("direct.historyRunning"),
    RETRY_PENDING: t("direct.historyRetry"),
    COMPLETED: t("direct.historyDone"),
    PARTIAL: t("direct.historyPartial"),
    FAILED_SAFE: t("direct.historyFailed"),
  };
  return (
    <section className="rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-4 shadow-[var(--shadow-card)]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-black">{statusLabel[sync.status] ?? t("direct.unknownStatus")}</p>
          <p className="mt-1 text-sm text-text-secondary">
            {t("direct.historyCounts", { synced: sync.conversations_synced, discovered: sync.conversations_discovered, imported: sync.messages_imported, existing: sync.messages_existing })}
          </p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-black ${active ? "bg-violet-500/15 text-primary" : sync.status === "FAILED_SAFE" ? "bg-rose-500/15 text-rose-600" : "bg-emerald-500/15 text-emerald-700"}`}>
          {statusLabel[sync.status] ?? t("direct.unknownStatus")}
        </span>
      </div>
      {sync.messages_unavailable > 0 || sync.error_count > 0 ? (
        <p className="mt-2 text-xs font-semibold text-amber-700">
          {t("direct.historyErrors", { unavailable: sync.messages_unavailable, errors: sync.error_count })}
        </p>
      ) : null}
    </section>
  );
}

function ParticipantAvatar({ conversation, size = "md" }: { conversation: DirectConversation; size?: "sm" | "md" | "lg" }) {
  const { t } = useI18n();
  const className = size === "lg" ? "h-16 w-16 text-xl" : size === "sm" ? "h-10 w-10 text-sm" : "h-12 w-12 text-base";
  const label = conversation.participant_display_name ?? conversation.participant_username ?? t("direct.customer");
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
  const { t } = useI18n();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const matchesFilter = (item: DirectConversation, candidate: string) => candidate === "unread" ? item.unread_count > 0 : candidate === "instagram" ? item.channel === "INSTAGRAM" : candidate === "intent" ? orderIntentConversationIds.has(item.id) : true;
  const searched = conversations.filter((item) => `${item.participant_display_name ?? ""} ${item.participant_username ?? ""}`.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase().replace(/^@/, "")));
  const orderedConversations = searched.filter((item) => matchesFilter(item, filter)).sort((left, right) => {
      const orderDifference = Number(orderIntentConversationIds.has(right.id)) - Number(orderIntentConversationIds.has(left.id));
      if (orderDifference) return orderDifference;
      const unreadDifference = right.unread_count - left.unread_count;
      if (unreadDifference) return unreadDifference;
      return new Date(right.last_message_at ?? 0).getTime() - new Date(left.last_message_at ?? 0).getTime();
    });

  if (loading) return <aside className="rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-3"><LoadingSkeleton /></aside>;
  if (error) return <aside className="rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-3"><ErrorState title={t("direct.listError")}  description={t("direct.listErrorHint")}  /></aside>;
  return (
    <aside className="flex h-full min-h-0 min-w-0 flex-col rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-3 shadow-[var(--shadow-card)]" data-direct-list>
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="font-black">{t("direct.dialogs")}</h2>
        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-black ${liveError ? "bg-rose-500/15 text-rose-600" : isLive ? "bg-emerald-500/15 text-emerald-600" : "bg-amber-500/15 text-amber-600"}`}>
          {liveError ? <WifiOff className="h-3 w-3" /> : <Wifi className="h-3 w-3" />}
          {liveError ? t("direct.offline") : isLive ? t("direct.live") : "…"}
        </span>
      </div>
      <input aria-label={t("direct.search")} value={search} onChange={(event) => setSearch(event.target.value)} className="mb-3 min-h-11 w-full rounded-2xl border border-border-subtle bg-surface-2 px-3 text-sm" placeholder={t("direct.search")} />
      <div className="flex flex-wrap gap-1 pb-3" role="group" aria-label={t("direct.filters")}>
        {["all", "unread", "instagram", "intent"].map((candidate) => <button type="button" key={candidate} aria-pressed={filter === candidate} onClick={() => setFilter(candidate)} className={`min-h-9 rounded-xl px-2 text-xs font-bold ${filter === candidate ? "bg-primary/15 text-primary" : "bg-surface-2 text-text-secondary"}`}>{t(`direct.filter.${candidate}`)} ({searched.filter((item) => matchesFilter(item, candidate)).length})</button>)}
      </div>
      {!conversations.length ? <DirectEmptyState instagramStatus={instagramStatus} /> : !orderedConversations.length ? <div role="status"><EmptyState title={t("direct.filteredEmpty")} description={t("direct.filteredHint")} /><Button variant="secondary" onClick={() => { setSearch(""); setFilter("all"); }}>{t("direct.resetFilters")}</Button></div> : (
        <div className="sellora-scrollbar min-h-0 flex-1 space-y-2 overflow-y-auto">
          {orderedConversations.map((item) => {
            const orderIntent = orderIntentConversationIds.has(item.id);
            return (
              <button type="button" key={item.id} onClick={() => onSelect(item.id)} aria-pressed={selectedId === item.id} data-conversation-id={item.id} className={`w-full rounded-2xl border p-3 text-left transition ${orderIntent ? "border-amber-500/50 bg-amber-500/10" : selectedId === item.id ? "border-primary bg-primary/10" : "border-border-subtle bg-surface-2"}`}>
                <div className="flex items-start gap-3">
                  <ParticipantAvatar conversation={item} size="sm" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <h3 className="flex items-center gap-1 truncate font-black">{item.participant_display_name ?? t("direct.customer")}{item.participant_is_verified_user ? <BadgeCheck className="h-4 w-4 shrink-0 text-sky-500" /> : null}</h3>
                        <p className="truncate text-xs text-text-muted">{item.participant_username ? `@${item.participant_username}` : item.participant_scoped_id ?? "—"}</p>
                      </div>
                      {item.unread_count ? <span className="rounded-full bg-rose-500 px-2 py-0.5 text-xs font-black text-white">{item.unread_count}</span> : null}
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {orderIntent ? <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2 py-1 text-xs font-black text-amber-700"><ShoppingBag className="h-3 w-3" />Ймовірне замовлення</span> : null}
                      {item.linked_order_id ? <span className="rounded-full bg-blue-500/15 px-2 py-1 text-xs font-bold text-blue-700">{t("direct.orderCreated")}</span> : item.linked_customer_id ? <span className="rounded-full bg-cyan-500/15 px-2 py-1 text-xs font-bold text-cyan-700">{t("direct.prospect")}</span> : null}
                      <span className="rounded-full bg-violet-500/15 px-2 py-1 text-xs font-bold text-primary">{item.channel === "INSTAGRAM" ? "Instagram" : t("direct.synthetic")}</span>

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
  const { t } = useI18n();
  if (!instagramStatus || instagramStatus.status === "DISCONNECTED" || !instagramStatus.token_present) return <EmptyState title={t("direct.disconnectedTitle")}  description={t("direct.disconnectedHint")}  />;
  if (!instagramStatus.webhook_active) return <EmptyState title={t("direct.webhookTitle")}  description={t("direct.webhookHint")}  />;
  return <EmptyState title={t("direct.noMessages")}  description={t("direct.noMessagesHint")}  />;
}

type PrepareResult = { ready: boolean; blockers: string[]; warnings: string[]; message_preview: string };

function MessageThread({
  conversation,
  automation,
  automationLoading,
  automationError,
  canManage,
  ensuringCustomer,
  onEnsureCustomer,
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
  prepareError,
  sendOutcome,
  sendPending,
  noAutoSend,
}: {
  conversation?: DirectConversation | null;
  automation?: DirectCustomerAutomationState;
  automationLoading: boolean;
  automationError: boolean;
  canManage: boolean;
  ensuringCustomer: boolean;
  onEnsureCustomer: () => void;
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
  prepareError: boolean;
  sendOutcome?: string;
  sendPending: boolean;
  noAutoSend: string;
}) {
  const { t } = useI18n();
  const scrollContainer = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = scrollContainer.current;
    if (!element) return;
    element.scrollTo({ top: element.scrollHeight, behavior: messages.length > 1 ? "smooth" : "auto" });
  }, [conversation?.id, messages.length]);

  if (!conversation) return <section className="rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-4"><EmptyState title={t("direct.selectTitle")}  description={t("direct.selectHint")}  /></section>;
  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 shadow-[var(--shadow-card)]">
      <div ref={scrollContainer} className="sellora-scrollbar min-h-0 flex-1 space-y-3 overflow-y-auto" data-direct-live-thread>
      <ParticipantProfileCard conversation={conversation} onRefresh={onRefreshProfile} refreshing={profileRefreshing} />
      <CustomerAutomationCard
        conversation={conversation}
        automation={automation}
        loading={automationLoading}
        error={automationError}
        canManage={canManage}
        ensuring={ensuringCustomer}
        onEnsure={onEnsureCustomer}
      />
      <div className="space-y-3 p-3">
        {loading ? <LoadingSkeleton /> : null}
        {error ? <ErrorState title={t("direct.messagesError")}  description={t("direct.messagesErrorHint")}  /> : null}
        {!loading && !error && messages.length === 0 ? <EmptyState title={t("direct.noMessages")}  description={t("direct.messagesEmptyHint")}  /> : null}
        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.direction === "OUTBOUND" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[82%] break-words rounded-2xl px-4 py-3 text-sm ${message.direction === "OUTBOUND" ? "bg-primary/15 text-text-primary" : "bg-surface-2"}`}>
              <p className="mb-1 text-xs font-black text-text-muted">{t(`direct.direction.${message.direction}`)} · {messageStatusLabel(message, t)}</p>
              <p>{message.text}</p>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-text-muted">
                {message.edit_count ? <span>{t("direct.edited", { count: message.edit_count })}</span> : null}
                {message.reaction ? <span className="rounded-full bg-surface-1 px-2 py-0.5">{message.reaction}</span> : null}
              </div>
            </div>
          </div>
        ))}
      </div>
      </div>
      <footer className="shrink-0 border-t border-border-subtle p-3">
        <div className="mb-2 text-xs text-text-muted">{noAutoSend}</div>
        <textarea aria-label={t("direct.reply")} disabled={!canManage} value={replyText} onChange={(event) => setReplyText(event.target.value)} className="h-20 min-h-12 w-full rounded-2xl border border-border-subtle bg-surface-2 p-3 text-sm" placeholder={t("direct.reply")} />
        <div className="mt-2 flex flex-wrap gap-2">
          <Button variant="secondary" onClick={onPrepare} disabled={!canManage || !replyText}>{t("direct.prepare")}</Button>
          <Button onClick={onSend} disabled={sendDisabled || !replyText}>{sendPending ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}{t("direct.send")}</Button>
        </div>
        {prepareResult ? <p role="status" className="mt-2 text-sm text-text-secondary">{t(prepareResult.ready ? "direct.ready" : "direct.blocked")}</p> : null}
        {prepareError ? <p role="alert" className="mt-2 text-sm text-rose-600">{t("direct.prepareError")}</p> : null}
        {sendOutcome ? <p role="status" className="mt-2 text-sm text-text-secondary">{t(`direct.sendState.${["SENT", "SENDING", "FAILED_SAFE", "RETRY_PENDING", "RECONCILIATION_REQUIRED"].includes(sendOutcome) ? sendOutcome : "UNKNOWN"}`)}</p> : null}
      </footer>
    </section>
  );
}

function CustomerAutomationCard({
  conversation,
  automation,
  loading,
  error,
  canManage,
  ensuring,
  onEnsure,
}: {
  conversation: DirectConversation;
  automation?: DirectCustomerAutomationState;
  loading: boolean;
  error: boolean;
  canManage: boolean;
  ensuring: boolean;
  onEnsure: () => void;
}) {
  const { t } = useI18n();
  const customer = automation?.customer;
  const missingLabels: Record<string, string> = {
    name: t("direct.fullName"),
    phone: t("direct.phone"),
    city: t("direct.city"),
    delivery_address: t("direct.warehouse"),
  };
  if (loading) return <div className="border-b border-border-subtle px-4 py-3"><LoadingSkeleton rows={1} /></div>;
  return (
    <section className="border-b border-border-subtle bg-surface-2/60 px-4 py-3" data-direct-customer-automation>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-black">{t("direct.orderSection")}</p>
            <span className={`rounded-full px-2 py-1 text-xs font-black ${automation?.profile_complete ? "bg-emerald-500/15 text-emerald-700" : customer ? "bg-amber-500/15 text-amber-700" : "bg-surface-1 text-text-muted"}`}>
              {automation?.profile_complete ? t("direct.profileComplete") : customer ? t("direct.prospect") : t("direct.notCreated")}
            </span>
          </div>
          {customer ? (
            <p className="mt-1 text-sm text-text-secondary">
              {customer.name}{customer.instagram_username ? ` · @${customer.instagram_username}` : ""}
            </p>
          ) : (
            <p className="mt-1 text-sm text-text-secondary">{t("direct.prospectHint")}</p>
          )}
          {automation?.missing_fields.length ? (
            <p className="mt-1 text-xs font-semibold text-amber-700">{t("direct.missingFields", { fields: automation.missing_fields.map((field) => missingLabels[field] ?? t("direct.otherField")).join(", ") })}</p>
          ) : null}
          {error ? <p className="mt-1 text-xs font-semibold text-rose-600">{t("direct.customerError")}</p> : null}
        </div>
        <div className="flex flex-wrap gap-2">
          {!customer && canManage ? (
            <Button variant="secondary" onClick={onEnsure} disabled={ensuring}>
              {ensuring ? <RefreshCw className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
              {t("direct.createProspect")}
            </Button>
          ) : null}
          {customer && !automation?.linked_order_id && canManage ? (
            <Link
              className="inline-flex min-h-10 items-center gap-2 rounded-2xl bg-primary px-4 py-2 text-sm font-black text-primary-foreground"
              href={`/orders?create=1&customer_id=${encodeURIComponent(customer.id)}&direct_conversation_id=${encodeURIComponent(conversation.id)}`}
            >
              <ShoppingBag className="h-4 w-4" />
              {t("direct.createOrder")}
            </Link>
          ) : null}
          {automation?.linked_order_id ? (
            <Link
              className="inline-flex min-h-10 items-center gap-2 rounded-2xl border border-border-subtle bg-surface-1 px-4 py-2 text-sm font-black text-primary"
              href={`/orders?order_id=${encodeURIComponent(automation.linked_order_id)}`}
            >
              <CheckCircle2 className="h-4 w-4" />
              {t("direct.openOrder")}
            </Link>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function messageStatusLabel(message: DirectMessage, t: (key: string) => string) {
  if (message.seen_at || message.delivery_status === "SEEN") return t("direct.seen");
  if (message.direction === "OUTBOUND" && message.delivery_status === "PROVIDER_ACCEPTED") return t("direct.accepted");
  if (message.direction === "INBOUND" && message.delivery_status === "RECEIVED") return t("direct.received");
  if (message.delivery_status === "FAILED") return t("direct.failed");
  return t("direct.unknownStatus");
}

function ParticipantProfileCard({ conversation, onRefresh, refreshing }: { conversation: DirectConversation; onRefresh: () => void; refreshing: boolean }) {
  const { t } = useI18n();
  const followers = conversation.participant_follower_count == null ? null : new Intl.NumberFormat("uk-UA").format(conversation.participant_follower_count);
  const profileReady = conversation.participant_profile_status === "READY";
  return (
    <header className="border-b border-border-subtle p-4">
      <div className="flex flex-wrap items-start gap-4">
        <ParticipantAvatar conversation={conversation} size="lg" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="truncate text-lg font-black">{conversation.participant_display_name ?? t("direct.customer")}</h2>
            {conversation.participant_is_verified_user ? <span className="inline-flex items-center gap-1 rounded-full bg-sky-500/15 px-2 py-1 text-xs font-bold text-sky-600"><BadgeCheck className="h-3.5 w-3.5" />{t("direct.verified")}</span> : null}
          </div>
          <p className="text-sm text-text-secondary">{conversation.participant_username ? `@${conversation.participant_username}` : t("direct.usernameUnavailable")}</p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs font-bold text-text-secondary">
            {followers ? <span className="inline-flex items-center gap-1 rounded-full bg-surface-2 px-2 py-1"><Users className="h-3.5 w-3.5" />{t("direct.followers", { count: followers })}</span> : null}
            {conversation.participant_is_user_follow_business === true ? <span className="rounded-full bg-emerald-500/15 px-2 py-1 text-emerald-700">{t("direct.followsShop")}</span> : null}
            {conversation.participant_is_business_follow_user === true ? <span className="rounded-full bg-violet-500/15 px-2 py-1 text-primary">{t("direct.shopFollows")}</span> : null}
          </div>
        </div>
        {conversation.channel === "INSTAGRAM" ? <Button variant="secondary" onClick={onRefresh} disabled={refreshing}>{refreshing ? <RefreshCw className="h-4 w-4 animate-spin" /> : <UserRound className="h-4 w-4" />}{profileReady ? t("direct.refreshProfile") : t("direct.loadProfile")}</Button> : null}
      </div>
      <p className="mt-3 text-sm text-text-secondary">{conversation.channel === "INSTAGRAM" ? "Instagram" : t("direct.synthetic")} · {conversation.messaging_window_expires_at ? t("direct.windowUntil", { date: new Date(conversation.messaging_window_expires_at).toLocaleString() }) : t("direct.windowUnavailable")}</p>
      {conversation.channel === "INSTAGRAM" && !profileReady ? <p className="mt-2 rounded-2xl bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-700">{conversation.participant_profile_status === "RETRY_PENDING" ? t("direct.profileRetry") : conversation.participant_profile_status === "UNAVAILABLE" ? t("direct.profileUnavailable") : t("direct.profileLoading")}</p> : null}
    </header>
  );
}

function AiPanel({ loading, suggestions, onAnalyze, analyzing, analysisError, onUseDraft, connectionStatus, embedded = false }: { loading: boolean; suggestions: AISuggestion[]; onAnalyze: () => void; analyzing: boolean; analysisError: boolean; onUseDraft: (text: string) => void; connectionStatus: string; embedded?: boolean }) {
  const { t } = useI18n();
  return <aside className={`${embedded ? "" : "h-full"} min-w-0 rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-4 shadow-[var(--shadow-card)]`} data-direct-ai-panel>
    {!embedded ? <h2 className="mb-3 flex items-center gap-2 font-black"><Bot className="h-5 w-5 text-primary" />{t("direct.aiPanel")}</h2> : null}
    <p className="mb-3 rounded-xl bg-surface-2 p-3 text-sm">{t(connectionStatus === "CONNECTED" ? "direct.connected" : "direct.disconnected")}</p>
    <Button onClick={onAnalyze} disabled={analyzing}><Sparkles className="h-4 w-4" />{t("direct.analyze")}</Button>
    {analysisError ? <p role="alert">{t("direct.analysisError")}</p> : null}
    <div className="mt-4 space-y-3 text-sm">{loading ? <LoadingSkeleton /> : null}
      {!loading && !suggestions.length ? <EmptyState title={t("direct.noSuggestions")} description={t("direct.suggestionHint")} /> : null}
      {suggestions.map((suggestion) => <section key={suggestion.id}><Card icon={<MessageCircle />} title={suggestion.title ?? t("direct.suggestion")} body={suggestion.draft_text ?? suggestion.summary ?? t("direct.suggestionHint")} />{suggestion.draft_text ? <Button variant="secondary" disabled={analyzing} onClick={() => onUseDraft(suggestion.draft_text!)}>{t("direct.useDraft")}</Button> : null}</section>)}
      <p className="text-xs text-text-muted">{t("direct.noAutoSend")}</p>
    </div>
  </aside>;
}

function Card({ title, body, icon }: { title: string; body: string; icon?: React.ReactNode }) {
  return <section className="rounded-2xl border border-border-subtle bg-surface-2 p-3"><div className="mb-1 flex items-center gap-2 font-black">{icon ? <span className="h-4 w-4 text-primary">{icon}</span> : <CheckCircle2 className="h-4 w-4 text-emerald-500" />}{title}</div><p className="text-text-secondary">{body}</p></section>;
}
