"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, ArrowRight, ArrowUpRight, CalendarDays, ChevronLeft, ChevronRight, CircleCheck, CreditCard, FlaskConical, LayoutDashboard, Search, Store } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Drawer } from "@/components/ui/overlay";
import { Button, Card, DataTable, EmptyState, FormField, Input, LoadingSkeleton, Select, StatusBadge } from "@/components/ui/primitives";
import { useI18n } from "@/i18n/provider";
import { ApiError } from "@/services/api";
import { platformAdminApi, type PlatformWorkspace, type SubscriptionStatus, type WorkspaceFilters } from "@/services/platform-admin";

import { PlatformActivity } from "./platform-activity";
import { accessDenied, PlatformProblem } from "./platform-feedback";

const defaultFilters: WorkspaceFilters = { search: "", active: "", demo: "", subscriptionStatus: "" };
const metrics = [
  { key: "total_workspaces", icon: Store, accent: "bg-violet-500/15 text-violet-300" },
  { key: "enabled_workspaces", icon: CircleCheck, accent: "bg-emerald-500/15 text-emerald-300" },
  { key: "workspaces_with_current_term", icon: CreditCard, accent: "bg-sky-500/15 text-sky-300" },
  { key: "demo_workspaces", icon: FlaskConical, accent: "bg-amber-500/15 text-amber-300" },
] as const;

const subscriptionTones = {
  UNMANAGED: "neutral", PENDING: "warning", TRIALING: "info", ACTIVE: "success",
  PAST_DUE: "danger", CANCELED: "neutral", EXPIRED: "neutral",
} as const satisfies Record<SubscriptionStatus, "neutral" | "warning" | "info" | "success" | "danger">;

const subscriptionStatuses = Object.keys(subscriptionTones) as SubscriptionStatus[];
const sections = [
  { id: "platform-overview", label: "platformAdmin.overviewNav", icon: LayoutDashboard },
  { id: "platform-directory", label: "platformAdmin.directoryNav", icon: Store },
  { id: "platform-activity", label: "platformAdmin.activityNav", icon: Activity },
] as const;

function SubscriptionBadge({ status }: { status: SubscriptionStatus }) {
  const { t } = useI18n();
  return <StatusBadge tone={subscriptionTones[status]}>{t(`platformAdmin.subscriptionStatus.${status}`)}</StatusBadge>;
}

function WorkspaceState({ workspace }: { workspace: PlatformWorkspace }) {
  const { t } = useI18n();
  return (
    <div className="flex flex-wrap gap-1.5">
      <StatusBadge tone={workspace.is_active ? "success" : "neutral"}>{t(workspace.is_active ? "platformAdmin.enabled" : "platformAdmin.disabled")}</StatusBadge>
      {workspace.is_demo ? <StatusBadge tone="info">{t("platformAdmin.demo")}</StatusBadge> : null}
    </div>
  );
}

function WorkspaceDirectory({ items, onSelect }: { items: PlatformWorkspace[]; onSelect: (id: string) => void }) {
  const { t, locale } = useI18n();
  const date = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeZone: "UTC" });
  const open = (workspace: PlatformWorkspace) => (
    <Button variant="ghost" size="sm" aria-label={t("platformAdmin.openWorkspace", { name: workspace.name })} onClick={() => onSelect(workspace.id)}>
      {t("platformAdmin.details")}<ArrowUpRight className="size-4 text-violet-400" aria-hidden="true" />
    </Button>
  );
  return (
    <>
      <div className="hidden lg:block">
        <DataTable>
          <table aria-label={t("platformAdmin.directory")} className="w-full table-fixed text-left text-sm">
            <thead className="bg-surface-2 text-xs text-text-secondary">
              <tr>
                <th scope="col" className="w-[27%] px-4 py-3.5">{t("platformAdmin.workspace")}</th>
                <th scope="col" className="w-[18%] px-4 py-3.5">{t("platformAdmin.workspaceStatus")}</th>
                <th scope="col" className="w-[12%] px-4 py-3.5">{t("platformAdmin.plan")}</th>
                <th scope="col" className="w-[19%] px-4 py-3.5">{t("platformAdmin.subscription")}</th>
                <th scope="col" className="px-4 py-3.5">{t("platformAdmin.created")}</th>
                <th scope="col" className="w-28 px-4 py-3.5"><span className="sr-only">{t("platformAdmin.details")}</span></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {items.map((workspace) => (
                <tr key={workspace.id} className="transition-colors hover:bg-surface-2 focus-within:bg-surface-2">
                  <th scope="row" className="min-w-0 break-words px-4 py-3.5">
                    <div className="flex min-w-0 items-center gap-3">
                      <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-violet-500/10 text-violet-300">
                        <Store className="size-4" aria-hidden="true" />
                      </span>
                      <span className="min-w-0">
                        <span className="block text-sm font-bold">{workspace.name}</span>
                        <span className="block text-xs font-normal text-text-secondary">{workspace.slug}</span>
                      </span>
                    </div>
                  </th>
                  <td className="px-4 py-3.5"><WorkspaceState workspace={workspace} /></td>
                  <td className="break-words px-4 py-3.5 text-text-secondary">{workspace.subscription.plan_code ?? t("platformAdmin.unassigned")}</td>
                  <td className="px-4 py-3.5"><SubscriptionBadge status={workspace.subscription.status} /></td>
                  <td className="px-4 py-3.5 text-xs tabular-nums text-text-secondary">{date.format(new Date(workspace.created_at))}</td>
                  <td className="px-2 py-3.5 text-right">{open(workspace)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </DataTable>
      </div>
      <ul aria-label={t("platformAdmin.directory")} className="grid gap-3 lg:hidden">
        {items.map((workspace) => (
          <li key={workspace.id}>
            <Card className="space-y-3">
              <div className="min-w-0 break-words">
                <h3 className="font-bold">{workspace.name}</h3>
                <p className="mt-1 text-xs text-text-secondary">{workspace.slug} · {date.format(new Date(workspace.created_at))}</p>
              </div>
              <WorkspaceState workspace={workspace} />
              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border-subtle pt-3">
                <div className="grid gap-1.5">
                  <SubscriptionBadge status={workspace.subscription.status} />
                  {workspace.subscription.plan_code ? <span className="break-all text-xs text-text-secondary">{workspace.subscription.plan_code}</span> : null}
                </div>
                {open(workspace)}
              </div>
            </Card>
          </li>
        ))}
      </ul>
    </>
  );
}

function WorkspaceProfile({ id, operatorId, onClose, recheckAccess, showActivity }: { id: string; operatorId: string; onClose: () => void; recheckAccess: () => void; showActivity: boolean }) {
  const { t, locale } = useI18n();
  const detail = useQuery({
    queryKey: ["platform-admin", operatorId, "workspace", id],
    queryFn: ({ signal }) => platformAdminApi.detail(id, signal),
    retry: false,
    gcTime: 0,
  });
  const denied = accessDenied(detail.error);
  useEffect(() => { if (denied) recheckAccess(); }, [denied, recheckAccess]);
  const workspace = detail.error ? undefined : detail.data;
  const number = new Intl.NumberFormat(locale);
  const date = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" });
  const formatDate = (value: string | null) => value ? date.format(new Date(value)) : t("platformAdmin.unassigned");
  const notFound = detail.error instanceof ApiError && detail.error.status === 404;

  return (
    <Drawer open title={workspace?.name ?? t("platformAdmin.profile")} description={workspace?.slug} onClose={onClose} className="dark text-text-primary">
      {detail.isPending ? <LoadingSkeleton title={t("common.loading")} rows={3} /> : null}
      {detail.error ? <PlatformProblem message={denied ? "forbidden" : notFound ? "notFound" : "error"} retry={denied || notFound ? undefined : () => void detail.refetch()} /> : null}
      {workspace ? (
        <div className="grid gap-4">
          <Card>
            <h3 className="mb-3 font-bold">{t("platformAdmin.workspaceInfo")}</h3>
            <WorkspaceState workspace={workspace} />
            <dl className="mt-4 grid grid-cols-2 gap-3 border-t border-border-subtle pt-4 text-sm">
              <dt className="text-text-secondary">{t("platformAdmin.activeMembers")}</dt><dd className="font-bold">{number.format(workspace.active_member_count)}</dd>
              <dt className="text-text-secondary">{t("platformAdmin.createdUtc")}</dt><dd>{formatDate(workspace.created_at)}</dd>
              <dt className="text-text-secondary">{t("platformAdmin.currency")}</dt><dd>{workspace.currency_code}</dd>
              <dt className="text-text-secondary">{t("platformAdmin.timezone")}</dt><dd className="break-all">{workspace.timezone}</dd>
              <dt className="text-text-secondary">{t("platformAdmin.workspaceId")}</dt><dd className="break-all font-mono text-xs">{workspace.id}</dd>
            </dl>
          </Card>
          <Card>
            <h3 className="mb-4 font-bold">{t("platformAdmin.subscription")}</h3>
            <dl className="grid grid-cols-2 items-start gap-3 text-sm">
              <dt className="text-text-secondary">{t("platformAdmin.plan")}</dt><dd className="break-words">{workspace.subscription.plan_code ?? t("platformAdmin.unassigned")}</dd>
              <dt className="text-text-secondary">{t("platformAdmin.status")}</dt><dd><SubscriptionBadge status={workspace.subscription.status} /></dd>
              <dt className="text-text-secondary">{t("platformAdmin.periodStart")}</dt><dd>{formatDate(workspace.subscription.current_period_start)}</dd>
              <dt className="text-text-secondary">{t("platformAdmin.periodEnd")}</dt><dd>{formatDate(workspace.subscription.current_period_end)}</dd>
            </dl>
            {workspace.subscription.cancel_at_period_end ? <p className="mt-4 text-sm text-[var(--warning-foreground)]">{t("platformAdmin.cancelAtEnd")}</p> : null}
          </Card>
          {showActivity ? <PlatformActivity operatorId={operatorId} workspaceId={id} recheckAccess={recheckAccess} /> : null}
        </div>
      ) : null}
    </Drawer>
  );
}

export function PlatformDashboard({ operatorId, recheckAccess, showActivity }: { operatorId: string; recheckAccess: () => void; showActivity: boolean }) {
  const { t, locale } = useI18n();
  const [filters, setFilters] = useState(defaultFilters);
  const [draft, setDraft] = useState(defaultFilters);
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const [selected, setSelected] = useState<string | null>(null);
  const closeProfile = useCallback(() => setSelected(null), []);
  const cursor = cursors[cursors.length - 1];
  const summary = useQuery({
    queryKey: ["platform-admin", operatorId, "summary"],
    queryFn: ({ signal }) => platformAdminApi.summary(signal),
    retry: false, gcTime: 0,
  });
  const directory = useQuery({
    queryKey: ["platform-admin", operatorId, "workspaces", filters, cursor],
    queryFn: ({ signal }) => platformAdminApi.workspaces(filters, cursor, signal),
    retry: false, gcTime: 0,
  });
  const denied = accessDenied(summary.error) || accessDenied(directory.error);
  useEffect(() => { if (denied) recheckAccess(); }, [denied, recheckAccess]);
  const filtered = Object.values(filters).some(Boolean);
  const hasDraft = Object.values(draft).some(Boolean);
  const items = directory.data?.items ?? [];
  const nextCursor = directory.data?.next_cursor;
  const number = new Intl.NumberFormat(locale);
  const time = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" });

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFilters({ ...draft, search: draft.search.trim() });
    setCursors([null]);
  }

  function clearFilters() {
    setFilters(defaultFilters);
    setDraft(defaultFilters);
    setCursors([null]);
  }

  if (denied) return <PlatformProblem message="forbidden" />;

  return (
    <div className="grid min-w-0 items-start gap-6 xl:grid-cols-[12rem_minmax(0,1fr)] xl:gap-9">
      <nav aria-label={t("platformAdmin.sections")} className="sticky top-0 z-20 flex flex-wrap gap-1 rounded-2xl border border-border-subtle bg-surface-1 p-1.5 shadow-[var(--shadow-card)] xl:top-8 xl:grid xl:p-2">
        {sections.filter(({ id }) => id !== "platform-activity" || showActivity).map(({ id, label, icon: Icon }) => (
          <a key={id} href={`#${id}`} className="flex min-h-10 items-center gap-2 rounded-xl px-2.5 text-sm font-semibold text-text-secondary transition-colors hover:bg-violet-500/10 hover:text-violet-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring xl:px-3">
            <Icon className="size-4 shrink-0 text-violet-300" aria-hidden="true" />
            {t(label)}
          </a>
        ))}
      </nav>

      <div className="grid min-w-0 gap-8 sm:gap-10">
        <section id="platform-overview" className="grid min-w-0 scroll-mt-32 gap-4 xl:scroll-mt-8" aria-labelledby="platform-title" tabIndex={-1}>
          <div className="relative isolate overflow-hidden rounded-[var(--radius-shell)] border border-violet-500/25 bg-surface-1 px-5 py-7 sm:px-8 sm:py-9">
            <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top_right,rgba(139,92,246,0.27),transparent_64%)]" aria-hidden="true" />
            <div className="relative flex flex-wrap items-end justify-between gap-5">
              <div className="min-w-0">
                <h1 id="platform-title" className="text-3xl font-bold tracking-tight sm:text-4xl">{t("platformAdmin.title")}</h1>
                <p className="mt-2 max-w-lg text-sm leading-6 text-text-secondary">{t("platformAdmin.description")}</p>
              </div>
              <a href="#platform-directory" className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-violet-400/35 bg-violet-500/15 px-3.5 text-sm font-semibold text-violet-100 transition-colors hover:bg-violet-500/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring">
                {t("platformAdmin.openDirectory")}<ArrowRight className="size-4" aria-hidden="true" />
              </a>
            </div>
          </div>
          {summary.isPending ? <LoadingSkeleton title={t("platformAdmin.loadingSummary")} rows={1} /> : null}
          {summary.error ? <PlatformProblem message="error" retry={() => void summary.refetch()} /> : null}
          {summary.data && !summary.error ? (
            <>
              <div role="group" aria-label={t("platformAdmin.summary")} className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
                {metrics.map(({ key, icon: Icon, accent }) => (
                  <Card key={key} className="min-w-0">
                    <div className={`mb-4 grid size-9 place-items-center rounded-xl ${accent}`}>
                      <Icon className="size-4" aria-hidden="true" />
                    </div>
                    <dl className="flex flex-col">
                      <dt className="order-last mt-1 text-xs font-semibold leading-5 text-text-secondary sm:text-sm">{t(`platformAdmin.metrics.${key}`)}</dt>
                      <dd data-testid={key} className="text-3xl font-bold tracking-tight tabular-nums">{number.format(summary.data[key])}</dd>
                    </dl>
                  </Card>
                ))}
              </div>
              <p className="flex items-center gap-2 text-xs text-text-secondary">
                <CalendarDays className="size-3.5" aria-hidden="true" />
                {t("platformAdmin.asOf", { time: time.format(new Date(summary.data.as_of)) })}
              </p>
            </>
          ) : null}
        </section>

        <section id="platform-directory" className="grid min-w-0 scroll-mt-32 gap-4 xl:scroll-mt-8" aria-labelledby="platform-directory-title" tabIndex={-1}>
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <h2 id="platform-directory-title" className="text-xl font-bold tracking-tight sm:text-2xl">{t("platformAdmin.directory")}</h2>
              <p className="mt-1 text-sm text-text-secondary">{t("platformAdmin.directoryDescription")}</p>
            </div>
            {directory.data && !directory.error ? (
              <span className="text-xs tabular-nums text-text-secondary" aria-live="polite">{t("platformAdmin.visibleRows", { count: number.format(items.length) })}</span>
            ) : null}
          </div>
          <form onSubmit={applyFilters} className="grid items-end gap-3 rounded-[var(--radius-card)] border border-border-subtle bg-surface-1 p-4 sm:grid-cols-2 lg:grid-cols-[minmax(0,1.4fr)_1fr_1fr_1.25fr] xl:grid-cols-[minmax(0,1.4fr)_1fr_1fr_1.25fr_auto]">
            <FormField label={t("platformAdmin.search")}>
              <Input name="search" value={draft.search} onChange={(event) => setDraft({ ...draft, search: event.target.value })} maxLength={120} placeholder={t("platformAdmin.searchPlaceholder")} />
            </FormField>
            <FormField label={t("platformAdmin.workspaceStatus")}>
              <Select name="active" value={draft.active} onChange={(event) => setDraft({ ...draft, active: event.target.value as WorkspaceFilters["active"] })}>
                <option value="">{t("platformAdmin.allStatuses")}</option>
                <option value="true">{t("platformAdmin.enabled")}</option>
                <option value="false">{t("platformAdmin.disabled")}</option>
              </Select>
            </FormField>
            <FormField label={t("platformAdmin.workspaceType")}>
              <Select name="demo" value={draft.demo} onChange={(event) => setDraft({ ...draft, demo: event.target.value as WorkspaceFilters["demo"] })}>
                <option value="">{t("platformAdmin.allTypes")}</option>
                <option value="false">{t("platformAdmin.standard")}</option>
                <option value="true">{t("platformAdmin.demo")}</option>
              </Select>
            </FormField>
            <FormField label={t("platformAdmin.subscriptionFilter")}>
              <Select name="subscriptionStatus" value={draft.subscriptionStatus} onChange={(event) => setDraft({ ...draft, subscriptionStatus: event.target.value as WorkspaceFilters["subscriptionStatus"] })}>
                <option value="">{t("platformAdmin.allStatuses")}</option>
                {subscriptionStatuses.map((status) => <option key={status} value={status}>{t(`platformAdmin.subscriptionStatus.${status}`)}</option>)}
              </Select>
            </FormField>
            <div className="flex flex-wrap gap-2">
              <Button type="submit" variant="brand"><Search className="size-4" aria-hidden="true" />{t("platformAdmin.applyFilters")}</Button>
              {filtered || hasDraft ? <Button variant="ghost" type="button" onClick={clearFilters}>{t("platformAdmin.reset")}</Button> : null}
            </div>
          </form>
          {directory.isPending ? <LoadingSkeleton title={t("platformAdmin.loadingDirectory")} /> : null}
          {directory.error ? <PlatformProblem message="error" retry={() => void directory.refetch()} /> : null}
          {directory.data && !directory.error ? (
            items.length
              ? <WorkspaceDirectory items={items} onSelect={setSelected} />
              : <EmptyState title={t(filtered ? "platformAdmin.filteredEmpty" : "platformAdmin.empty")} description={t(filtered ? "platformAdmin.filteredEmptyDescription" : "platformAdmin.emptyDescription")} />
          ) : null}
          {!directory.error && (cursors.length > 1 || nextCursor) ? (
            <nav className="flex flex-wrap items-center justify-between gap-2" aria-label={t("platformAdmin.pagination")}>
              <Button variant="secondary" size="sm" disabled={cursors.length === 1} onClick={() => setCursors((current) => current.slice(0, -1))}>
                <ChevronLeft className="size-4" aria-hidden="true" />{t("platformAdmin.previous")}
              </Button>
              <span className="text-xs tabular-nums text-text-secondary" aria-live="polite">{t("platformAdmin.page", { page: cursors.length })}</span>
              <Button variant="secondary" size="sm" disabled={!nextCursor} onClick={() => { if (nextCursor) setCursors((current) => [...current, nextCursor]); }}>
                {t("platformAdmin.next")}<ChevronRight className="size-4" aria-hidden="true" />
              </Button>
            </nav>
          ) : null}
        </section>

        {showActivity ? (
          <section id="platform-activity" aria-label={t("platformActivity.title")} className="scroll-mt-32 xl:scroll-mt-8" tabIndex={-1}>
            <PlatformActivity operatorId={operatorId} recheckAccess={recheckAccess} />
          </section>
        ) : null}
      </div>
      {selected ? <WorkspaceProfile key={selected} id={selected} operatorId={operatorId} onClose={closeProfile} recheckAccess={recheckAccess} showActivity={showActivity} /> : null}
    </div>
  );
}
