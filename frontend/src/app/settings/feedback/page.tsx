"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { FeedbackStatus, fetchPilotFeedback, updatePilotFeedbackStatus } from "@/services/feedback";

const STATUSES: FeedbackStatus[] = ["NEW", "REVIEWED", "PLANNED", "FIXED", "WONT_FIX"];

export default function FeedbackSettingsPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspace, currentWorkspaceId, status } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const canView = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";
  const canUpdate = currentWorkspace?.role === "OWNER";
  const enabled = status === "authenticated" && Boolean(currentUser) && Boolean(workspaceId) && canView;
  const feedback = useQuery({ queryKey: ["pilot-feedback", workspaceId], queryFn: () => fetchPilotFeedback(workspaceId), enabled });
  const updateStatus = useMutation({ mutationFn: ({ id, nextStatus }: { id: string; nextStatus: FeedbackStatus }) => updatePilotFeedbackStatus(workspaceId, id, nextStatus), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["pilot-feedback", workspaceId] }) });

  return (
    <main className="min-h-screen min-w-0 overflow-x-hidden bg-[#F8F7FC] p-4 text-slate-950 sm:p-6 dark:bg-[#101120] dark:text-white">
      <div className="mx-auto grid min-w-0 max-w-6xl gap-6">
        <header className="rounded-[28px] bg-white p-6 shadow-sm dark:bg-slate-900">
          <p className="text-sm font-black uppercase tracking-[0.22em] text-violet-600 dark:text-violet-300">{t("feedback.management.eyebrow")}</p>
          <h1 className="mt-3 text-3xl font-black">{t("feedback.management.title")}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">{t("feedback.management.description")}</p>
        </header>
        {!canView ? <ErrorState title={t("feedback.errors.restrictedTitle")} description={t("feedback.errors.restrictedDescription")} /> : null}
        {feedback.isLoading ? <LoadingSkeleton rows={4} title={t("feedback.management.loading")} /> : null}
        {feedback.isError ? <ErrorState description={t("feedback.errors.loadFailed")} onRetry={() => feedback.refetch()} /> : null}
        {canView && !feedback.isLoading && !feedback.data?.length ? <EmptyState title={t("feedback.management.emptyTitle")} description={t("feedback.management.emptyDescription")} /> : null}
        <section className="grid min-w-0 gap-3">
          {(feedback.data ?? []).map((item) => (
            <article className="min-w-0 overflow-hidden rounded-[24px] bg-white p-5 shadow-sm dark:bg-slate-900" key={item.id}>
              <div className="flex min-w-0 flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2 text-xs font-black uppercase tracking-[0.12em]"><span className="rounded-full bg-violet-50 px-3 py-1 text-violet-700 dark:bg-violet-400/10 dark:text-violet-100">{t(`feedback.categories.${item.category}`)}</span><span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600 dark:bg-white/10 dark:text-slate-200">{t(`feedback.statuses.${item.status}`)}</span>{item.rating ? <span className="rounded-full bg-amber-50 px-3 py-1 text-amber-700 dark:bg-amber-400/10 dark:text-amber-100">{t("feedback.management.rating", { rating: item.rating })}</span> : null}</div>
                  <p className="mt-3 line-clamp-3 break-words text-sm leading-6 text-slate-700 dark:text-slate-200">{item.message}</p>
                  <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{item.page_path ?? "—"} · {new Date(item.created_at).toLocaleDateString()}</p>
                </div>
                {canUpdate ? <select className="min-h-11 rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-white/10 dark:bg-white/10" value={item.status} onChange={(event) => updateStatus.mutate({ id: item.id, nextStatus: event.target.value as FeedbackStatus })} disabled={updateStatus.isPending}>{STATUSES.map((nextStatus) => <option key={nextStatus} value={nextStatus}>{t(`feedback.statuses.${nextStatus}`)}</option>)}</select> : null}
              </div>
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}
