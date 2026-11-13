"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, ArrowUpRight, CalendarDays, ChevronLeft, ChevronRight, CircleCheck, CreditCard, FlaskConical, Search, Store, Users } from "lucide-react";
import { useCallback, useEffect, useState, useSyncExternalStore, type FormEvent } from "react";
import { Drawer } from "@/components/ui/overlay";
import { Button, Card, DataTable, EmptyState, FormField, Input, LoadingSkeleton, Select, StatusBadge } from "@/components/ui/primitives";
import { useI18n } from "@/i18n/provider";
import { ApiError } from "@/services/api";
import { platformAdminApi, type PlatformWorkspace, type SubscriptionStatus, type WorkspaceFilters } from "@/services/platform-admin";

import { PlatformActivity } from "./platform-activity";
import { PlatformUsers } from "./platform-users";
import { accessDenied, PlatformProblem } from "./platform-feedback";

const defaultFilters: WorkspaceFilters = { search: "", active: "", demo: "", subscriptionStatus: "", archived: false };
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
  { id: "platform-users", label: "platformRegistry.users", icon: Users },
  { id: "platform-directory", label: "platformAdmin.directoryNav", icon: Store },
  { id: "platform-activity", label: "platformAdmin.activityNav", icon: Activity },
] as const;

function subscribeToSection(onChange: () => void) {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}

function getSection() {
  return window.location.hash.slice(1);
}

function getInitialSection() {
  return "";
}

function SubscriptionBadge({ status }: { status: SubscriptionStatus }) {
  const { t } = useI18n();
  return <StatusBadge tone={subscriptionTones[status]}>{t(`platformAdmin.subscriptionStatus.${status}`)}</StatusBadge>;
}

function WorkspaceState({ workspace }: { workspace: PlatformWorkspace }) {
  const { t } = useI18n();
  if (workspace.archived_at) return <StatusBadge tone="neutral">{t("platformRegistry.archived")}</StatusBadge>;
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

function WorkspaceTeam({ operatorId, workspaceId, recheckAccess }: {
  operatorId: string; workspaceId: string; recheckAccess: () => void;
}) {
  const { t } = useI18n();
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const cursor = cursors[cursors.length - 1];
  const team = useQuery({
    queryKey: ["platform-admin", operatorId, "workspace-team", workspaceId, cursor],
    queryFn: ({ signal }) => platformAdminApi.workspaceTeam(workspaceId, cursor, signal),
    retry: false,
    gcTime: 0,
  });
  const denied = accessDenied(team.error);
  useEffect(() => { if (denied) recheckAccess(); }, [denied, recheckAccess]);
  const page = team.error ? undefined : team.data;

  return (
    <Card>
      <h3 className="mb-3 font-bold">{t("platformRegistry.team.title")}</h3>
      {team.isPending ? <p role="status" className="text-sm text-text-secondary">{t("common.loading")}</p> : null}
      {team.error ? <PlatformProblem message={denied ? "forbidden" : "error"} retry={denied ? undefined : () => void team.refetch()} /> : null}
      {page && page.items.length === 0 ? <p className="text-sm text-text-secondary">{t("platformRegistry.team.empty")}</p> : null}
      {page && page.items.length > 0 ? (
        <ul className="divide-y divide-border-subtle">
          {page.items.map((member) => (
            <li key={member.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
              <p className="min-w-0 break-words text-sm font-semibold">{[member.first_name, member.last_name].filter(Boolean).join(" ")}</p>
              <div className="flex flex-wrap gap-1.5">
                <StatusBadge>{t(`platformRegistry.roles.${member.role}`)}</StatusBadge>
                <StatusBadge tone={member.is_active ? "success" : "neutral"}>
                  {t(member.is_active ? "platformRegistry.team.enabled" : "platformRegistry.team.disabled")}
                </StatusBadge>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
      {page && (cursors.length > 1 || page.next_cursor) ? (
        <div className="mt-3 flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" disabled={cursors.length === 1} onClick={() => setCursors((current) => current.slice(0, -1))}>
            {t("platformAdmin.previous")}
          </Button>
          <Button size="sm" variant="secondary" disabled={!page.next_cursor}
            onClick={() => setCursors((current) => [...current, page.next_cursor])}>
            {t("platformAdmin.next")}
          </Button>
        </div>
      ) : null}
    </Card>
  );
}

function WorkspaceProfile({ id, operatorId, onClose, recheckAccess, showActivity, canArchive, showTeam }: {
  id: string; operatorId: string; onClose: () => void; recheckAccess: () => void; showActivity: boolean; canArchive: boolean; showTeam: boolean;
}) {
  const { t, locale } = useI18n();
  const queryClient = useQueryClient();
  const [confirm, setConfirm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [failure, setFailure] = useState<"archiveConflict" | "archiveError">();
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
  const restoring = Boolean(workspace?.archived_at);
  const lifecycleAction = restoring ? "restore" : "archive";

  async function changeArchive() {
    setSaving(true);
    setFailure(undefined);
    try {
      await platformAdminApi.setArchived(id, !restoring);
      setConfirm(false);
      await queryClient.invalidateQueries({
        predicate: ({ queryKey }) => queryKey[0] === "platform-admin" && queryKey[1] === operatorId && queryKey[2] !== "identity",
      });
    } catch (error) {
      if (accessDenied(error)) recheckAccess();
      setFailure(error instanceof ApiError && error.status === 409 ? "archiveConflict" : "archiveError");
    } finally {
      setSaving(false);
    }
  }

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
          {showTeam ? <WorkspaceTeam operatorId={operatorId} workspaceId={id} recheckAccess={recheckAccess} /> : null}
          {showActivity ? <PlatformActivity operatorId={operatorId} workspaceId={id} recheckAccess={recheckAccess} /> : null}
          {canArchive && (restoring || workspace.archive_allowed) ? (
            <Card className="grid gap-3">
              <h3 className="font-bold">{t("platformRegistry.lifecycle")}</h3>
              <p className="text-sm text-text-secondary">{t(`platformRegistry.${lifecycleAction}Description`)}</p>
              {failure ? <p className="text-sm text-[var(--danger-foreground)]" role="alert">{t(`platformRegistry.${failure}`)}</p> : null}
              <div className="flex flex-wrap gap-2">
                {confirm ? (
                  <>
                    <Button variant={restoring ? "brand" : "danger"} loading={saving} onClick={() => void changeArchive()}>
                      {t(`platformRegistry.confirm.${lifecycleAction}`)}
                    </Button>
                    <Button variant="ghost" disabled={saving} onClick={() => setConfirm(false)}>{t("actions.cancel")}</Button>
                  </>
                ) : <Button variant="secondary" onClick={() => setConfirm(true)}>{t(`platformRegistry.${lifecycleAction}`)}</Button>}
              </div>
            </Card>
          ) : null}
        </div>
      ) : null}
    </Drawer>
  );
}

export function PlatformDashboard({ operatorId, recheckAccess, showActivity, showUsers, canArchive }: {
  operatorId: string; recheckAccess: () => void; showActivity: boolean; showUsers: boolean; canArchive: boolean;
}) {
  const { t } = useI18n();
  const [selected, setSelected] = useState<string | null>(null);
  const closeProfile = useCallback(() => setSelected(null), []);
  const requestedSection = useSyncExternalStore(subscribeToSection, getSection, getInitialSection);
  const availableSections = sections.filter(({ id }) =>
    (id !== "platform-users" || showUsers) && (id !== "platform-activity" || showActivity));
  const currentSection = availableSections.find(({ id }) => id === requestedSection) ?? availableSections[0];

  return (
    <div className="grid min-w-0 items-start gap-6 md:grid-cols-[11rem_minmax(0,1fr)] lg:grid-cols-[13rem_minmax(0,1fr)] lg:gap-8">
      <nav aria-label={t("platformAdmin.sections")} className="sticky top-0 z-20 grid grid-flow-col auto-cols-fr gap-1 rounded-xl border border-border-subtle bg-surface-1 p-1.5 md:top-6 md:grid-flow-row md:p-2">
        {availableSections.map(({ id, label, icon: Icon }) => (
          <a key={id} href={`#${id}`} aria-current={id === currentSection.id ? "page" : undefined}
            className="flex min-h-11 min-w-0 flex-col items-center justify-center gap-1.5 rounded-lg px-1 text-center text-xs font-semibold text-text-secondary outline-none transition-colors hover:bg-surface-2 hover:text-text-primary focus-visible:ring-2 focus-visible:ring-focus-ring aria-[current=page]:bg-violet-500/15 aria-[current=page]:text-violet-200 sm:flex-row sm:px-3 sm:text-sm md:justify-start">
            <Icon className="size-4 shrink-0" aria-hidden="true" />
            {t(label)}
          </a>
        ))}
      </nav>
      <div className="min-w-0">
        {currentSection.id === "platform-users" ? <PlatformUsers operatorId={operatorId} recheckAccess={recheckAccess} onOpenWorkspace={setSelected} /> : null}
        {currentSection.id === "platform-directory" ? <PlatformWorkspaces operatorId={operatorId} recheckAccess={recheckAccess} onOpenWorkspace={setSelected} /> : null}
        {currentSection.id === "platform-activity" ? (
          <section id="platform-activity" className="grid scroll-mt-24 gap-5 md:scroll-mt-6" aria-labelledby="platform-activity-title" tabIndex={-1}>
            <h1 id="platform-activity-title" className="text-2xl font-bold tracking-tight sm:text-3xl">{t("platformAdmin.activityNav")}</h1>
            <PlatformActivity operatorId={operatorId} recheckAccess={recheckAccess} />
          </section>
        ) : null}
      </div>
      {selected ? <WorkspaceProfile key={selected} id={selected} operatorId={operatorId} onClose={closeProfile} recheckAccess={recheckAccess} showActivity={showActivity} canArchive={canArchive} showTeam={showUsers} /> : null}
    </div>
  );
}

function PlatformWorkspaces({ operatorId, recheckAccess, onOpenWorkspace }: {
  operatorId: string; recheckAccess: () => void; onOpenWorkspace: (id: string) => void;
}) {
  const { t, locale } = useI18n();
  const [filters, setFilters] = useState(defaultFilters);
  const [draft, setDraft] = useState(defaultFilters);
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
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
  const filtered = Boolean(filters.search || filters.active || filters.demo || filters.subscriptionStatus);
  const hasDraft = Boolean(draft.search || draft.active || draft.demo || draft.subscriptionStatus);
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
    const reset = { ...defaultFilters, archived: filters.archived };
    setFilters(reset);
    setDraft(reset);
    setCursors([null]);
  }

  function switchArchive(archived: boolean) {
    const next = { ...defaultFilters, search: filters.search, archived };
    setFilters(next);
    setDraft(next);
    setCursors([null]);
  }

  if (denied) return <PlatformProblem message="forbidden" />;

  return (
    <section id="platform-directory" className="grid min-w-0 scroll-mt-24 gap-5 md:scroll-mt-6" aria-labelledby="platform-directory-title" tabIndex={-1}>
      <div>
        <h1 id="platform-directory-title" className="text-2xl font-bold tracking-tight sm:text-3xl">{t("platformAdmin.directory")}</h1>
        <p className="mt-1 text-sm text-text-secondary">{t("platformAdmin.directoryDescription")}</p>
      </div>
      {summary.isPending ? <LoadingSkeleton title={t("platformAdmin.loadingSummary")} rows={1} /> : null}
      {summary.error ? <PlatformProblem message="error" retry={() => void summary.refetch()} /> : null}
      {summary.data && !summary.error ? (
        <>
          <div role="group" aria-label={t("platformAdmin.summary")} className="grid grid-cols-2 gap-2.5 xl:grid-cols-4">
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
      {directory.data && !directory.error ? (
        <p className="text-xs tabular-nums text-text-secondary" aria-live="polite">{t("platformAdmin.visibleRows", { count: number.format(items.length) })}</p>
      ) : null}
      <div className="flex flex-wrap gap-2" role="group" aria-label={t("platformAdmin.directory")}>
        <Button size="sm" variant={filters.archived ? "ghost" : "secondary"} aria-pressed={!filters.archived} onClick={() => switchArchive(false)}>
          {t("platformRegistry.current")}
        </Button>
        <Button size="sm" variant={filters.archived ? "secondary" : "ghost"} aria-pressed={filters.archived} onClick={() => switchArchive(true)}>
          {t("platformRegistry.archiveTab")}
          {summary.data && !summary.error && summary.data.archived_workspaces !== undefined ? number.format(summary.data.archived_workspaces) : null}
        </Button>
      </div>
      <form onSubmit={applyFilters} className="grid items-end gap-3 rounded-[var(--radius-card)] border border-border-subtle bg-surface-1 p-4 sm:grid-cols-2 xl:grid-cols-[minmax(0,1.4fr)_1fr_1fr_1.25fr] 2xl:grid-cols-[minmax(0,1.4fr)_1fr_1fr_1.25fr_auto]">
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
          ? <WorkspaceDirectory items={items} onSelect={onOpenWorkspace} />
          : <EmptyState title={t(filtered ? "platformAdmin.filteredEmpty" : filters.archived ? "platformRegistry.archiveEmpty" : "platformAdmin.empty")} description={t(filtered ? "platformAdmin.filteredEmptyDescription" : filters.archived ? "platformRegistry.archiveEmptyDescription" : "platformAdmin.emptyDescription")} />
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
  );
}
