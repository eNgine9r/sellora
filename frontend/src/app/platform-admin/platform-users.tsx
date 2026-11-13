"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, ChevronLeft, ChevronRight, FlaskConical, Search, Store, UserCheck, Users } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Drawer } from "@/components/ui/overlay";
import { Button, Card, DataTable, EmptyState, FormField, Input, LoadingSkeleton, Select, StatusBadge } from "@/components/ui/primitives";
import { useI18n } from "@/i18n/provider";
import { ApiError } from "@/services/api";
import { platformAdminApi, type PlatformUser, type PlatformUserFilters } from "@/services/platform-admin";
import { accessDenied, PlatformProblem } from "./platform-feedback";

const defaultFilters: PlatformUserFilters = { search: "", segment: "", active: "" };
const segments = ["", "STANDARD", "DEMO_ONLY", "NO_ENABLED_WORKSPACE"] as const;
const metrics = [
  { key: "total_accounts", icon: Users },
  { key: "enabled_accounts", icon: UserCheck },
  { key: "demo_only_accounts", icon: FlaskConical },
  { key: "accounts_without_enabled_workspace", icon: Store },
] as const;

function userName(user: PlatformUser) {
  return [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email;
}

function AccountStatus({ user }: { user: PlatformUser }) {
  const { t } = useI18n();
  return (
    <StatusBadge tone={user.is_active ? "success" : "neutral"}>
      {t(user.is_active ? "platformRegistry.userEnabled" : "platformRegistry.userDisabled")}
    </StatusBadge>
  );
}

function AccountSegment({ user }: { user: PlatformUser }) {
  const { t } = useI18n();
  return <StatusBadge tone={user.segment === "DEMO_ONLY" ? "info" : "neutral"}>{t(`platformRegistry.segments.${user.segment}`)}</StatusBadge>;
}

function AccountAvatar({ user }: { user: PlatformUser }) {
  const initials = [user.first_name, user.last_name].filter(Boolean).map((name) => Array.from(name.trim())[0]).join("");
  return (
    <span className="grid size-10 shrink-0 place-items-center rounded-xl border border-violet-400/20 bg-violet-500/10 text-sm font-semibold uppercase text-violet-200" aria-hidden="true">
      {initials || Array.from(user.email)[0]}
    </span>
  );
}

function RegistryPagination({ page, nextCursor, onPrevious, onNext }: {
  page: number; nextCursor: string | null | undefined; onPrevious: () => void; onNext: (cursor: string) => void;
}) {
  const { t } = useI18n();
  if (page === 1 && !nextCursor) return null;
  return (
    <nav className="flex flex-wrap items-center justify-between gap-2" aria-label={t("platformRegistry.pagination")}>
      <Button size="sm" variant="secondary" disabled={page === 1} onClick={onPrevious}>
        <ChevronLeft className="size-4" aria-hidden="true" />{t("platformAdmin.previous")}
      </Button>
      <span className="text-xs text-text-secondary" aria-live="polite">{t("platformAdmin.page", { page })}</span>
      <Button size="sm" variant="secondary" disabled={!nextCursor} onClick={() => { if (nextCursor) onNext(nextCursor); }}>
        {t("platformAdmin.next")}<ChevronRight className="size-4" aria-hidden="true" />
      </Button>
    </nav>
  );
}

function UserProfile({ userId, operatorId, close, recheckAccess, onOpenWorkspace }: {
  userId: string; operatorId: string; close: () => void; recheckAccess: () => void; onOpenWorkspace: (id: string) => void;
}) {
  const { t, locale } = useI18n();
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const cursor = cursors[cursors.length - 1];
  const detail = useQuery({
    queryKey: ["platform-admin", operatorId, "user", userId, cursor],
    queryFn: ({ signal }) => platformAdminApi.user(userId, cursor, signal),
    retry: false, gcTime: 0,
  });
  const denied = accessDenied(detail.error);
  useEffect(() => { if (denied) recheckAccess(); }, [denied, recheckAccess]);
  const user = detail.error ? undefined : detail.data;
  const missing = detail.error instanceof ApiError && detail.error.status === 404;
  const date = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" });

  return (
    <Drawer open title={user ? userName(user) : t("platformRegistry.profile")} onClose={close} className="dark text-text-primary">
      {detail.isPending ? <LoadingSkeleton title={t("common.loading")} rows={2} /> : null}
      {detail.error ? <PlatformProblem message={denied ? "forbidden" : "error"} retry={denied || missing ? undefined : () => void detail.refetch()} /> : null}
      {user ? (
        <div className="grid gap-4">
          <Card className="grid gap-4">
            <div className="flex items-center gap-3">
              <AccountAvatar user={user} />
              <div className="min-w-0">
                <p className="break-all text-sm text-text-secondary">{user.email}</p>
                <div className="mt-2 flex flex-wrap gap-1.5"><AccountStatus user={user} /><AccountSegment user={user} /></div>
              </div>
            </div>
            <dl className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-3 border-t border-border-subtle pt-4 text-sm">
              <dt className="text-text-secondary">{t("platformRegistry.createdColumn")}</dt>
              <dd>{date.format(new Date(user.created_at))}</dd>
              <dt className="text-text-secondary">{t("platformRegistry.lastLogin")}</dt>
              <dd>{user.last_login_at ? date.format(new Date(user.last_login_at)) : t("platformRegistry.noLogin")}</dd>
              <dt className="text-text-secondary">{t("platformRegistry.ownedWorkspaces")}</dt>
              <dd className="font-semibold tabular-nums">{new Intl.NumberFormat(locale).format(user.owned_workspace_count)}</dd>
              <dt className="text-text-secondary">{t("platformRegistry.accountId")}</dt>
              <dd className="break-all font-mono text-xs">{user.id}</dd>
            </dl>
          </Card>
          <Card className="grid gap-2">
            <h3 className="font-semibold">{t("platformRegistry.accountBilling")}</h3>
            <p className="text-sm leading-6 text-text-secondary">{t("platformRegistry.billingUnavailable")}</p>
          </Card>
          <Card className="grid gap-3">
            <h3 className="font-bold">{t("platformRegistry.linkedWorkspaces")}</h3>
            {user.workspaces.length ? (
              <ul className="divide-y divide-border-subtle">
                {user.workspaces.map((workspace) => (
                  <li key={workspace.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                    <div className="min-w-0">
                      <p className="break-words text-sm font-semibold">{workspace.name}</p>
                      <div className="mt-1 flex flex-wrap items-center gap-2">
                        <StatusBadge>{t(`platformRegistry.roles.${workspace.role}`)}</StatusBadge>
                        {workspace.archived_at ? <StatusBadge tone="neutral">{t("platformRegistry.archived")}</StatusBadge> :
                          !workspace.is_active ? <StatusBadge tone="neutral">{t("platformAdmin.disabled")}</StatusBadge> : null}
                      </div>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => { close(); onOpenWorkspace(workspace.id); }}>
                      {t("platformAdmin.details")}<ArrowUpRight className="size-4" aria-hidden="true" />
                    </Button>
                  </li>
                ))}
              </ul>
            ) : <p className="text-sm text-text-secondary">{t("platformRegistry.noLinkedWorkspaces")}</p>}
            <RegistryPagination page={cursors.length} nextCursor={user.next_cursor}
              onPrevious={() => setCursors((values) => values.slice(0, -1))}
              onNext={(next) => setCursors((values) => [...values, next])} />
          </Card>
        </div>
      ) : null}
    </Drawer>
  );
}

export function PlatformUsers({ operatorId, recheckAccess, onOpenWorkspace }: {
  operatorId: string; recheckAccess: () => void; onOpenWorkspace: (id: string) => void;
}) {
  const { t, locale } = useI18n();
  const [draft, setDraft] = useState(defaultFilters);
  const [filters, setFilters] = useState(defaultFilters);
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const [selected, setSelected] = useState<string | null>(null);
  const close = useCallback(() => setSelected(null), []);
  const cursor = cursors[cursors.length - 1];
  const directory = useQuery({
    queryKey: ["platform-admin", operatorId, "users", filters, cursor],
    queryFn: ({ signal }) => platformAdminApi.users(filters, cursor, signal),
    retry: false, gcTime: 0,
  });
  const summary = useQuery({
    queryKey: ["platform-admin", operatorId, "users-summary"],
    queryFn: ({ signal }) => platformAdminApi.userSummary(signal),
    retry: false, gcTime: 0,
  });
  const denied = accessDenied(directory.error) || accessDenied(summary.error);
  useEffect(() => { if (denied) recheckAccess(); }, [denied, recheckAccess]);

  function submit(event: FormEvent) {
    event.preventDefault();
    setCursors([null]);
    setFilters({ ...draft, segment: filters.segment, search: draft.search.trim() });
  }

  function selectSegment(segment: PlatformUserFilters["segment"]) {
    setCursors([null]);
    setFilters({ ...filters, segment });
  }

  function clearFilters() {
    setDraft(defaultFilters);
    setFilters(defaultFilters);
    setCursors([null]);
  }

  const date = new Intl.DateTimeFormat(locale, { dateStyle: "medium" });
  const number = new Intl.NumberFormat(locale);
  const results = denied || directory.error ? undefined : directory.data;
  const counts = denied || summary.error ? undefined : summary.data;

  function openProfile(user: PlatformUser) {
    return (
      <Button variant="ghost" size="sm" aria-label={t("platformRegistry.openUser", { name: userName(user) })} onClick={() => setSelected(user.id)}>
        {t("platformAdmin.details")}<ArrowUpRight className="size-4 text-violet-300" aria-hidden="true" />
      </Button>
    );
  }

  if (denied) return <PlatformProblem message="forbidden" />;

  return (
    <section id="platform-users" className="grid min-w-0 scroll-mt-24 gap-5 md:scroll-mt-6" aria-labelledby="platform-users-title" tabIndex={-1}>
      <div>
        <h1 id="platform-users-title" className="text-2xl font-bold tracking-tight sm:text-3xl">{t("platformRegistry.users")}</h1>
        <p className="mt-1 max-w-2xl text-sm leading-6 text-text-secondary">{t("platformRegistry.consoleDescription")}</p>
      </div>

      {summary.isPending ? <LoadingSkeleton title={t("platformAdmin.loadingSummary")} rows={1} /> : null}
      {summary.error ? <PlatformProblem message="error" retry={() => void summary.refetch()} /> : null}
      {counts ? (
        <div className="grid grid-cols-2 gap-2.5 xl:grid-cols-4" role="group" aria-label={t("platformRegistry.summary")}>
          {metrics.map(({ key, icon: Icon }) => (
            <Card key={key} className="min-w-0 shadow-none">
              <Icon className="mb-2.5 size-4 text-violet-300" aria-hidden="true" />
              <dl>
                <dt className="text-xs font-medium leading-5 text-text-secondary">{t(`platformRegistry.metrics.${key}`)}</dt>
                <dd className="mt-1 text-2xl font-bold tracking-tight tabular-nums sm:text-3xl">{number.format(counts[key])}</dd>
              </dl>
            </Card>
          ))}
        </div>
      ) : null}

      <div className="grid min-w-0 gap-3">
        <div className="grid gap-3 rounded-[var(--radius-card)] border border-border-subtle bg-surface-1 p-3 sm:p-4">
          <div className="flex flex-wrap gap-1 border-b border-border-subtle pb-3" role="group" aria-label={t("platformRegistry.accountSegments")}>
            {segments.map((segment) => (
              <Button key={segment} size="sm" variant={filters.segment === segment ? "secondary" : "ghost"}
                aria-pressed={filters.segment === segment} onClick={() => selectSegment(segment)}>
                {t(segment ? `platformRegistry.segments.${segment}` : "platformRegistry.allAccounts")}
              </Button>
            ))}
          </div>
          <form onSubmit={submit} className="grid items-end gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(9rem,12rem)_auto]">
            <FormField label={t("platformRegistry.search")}>
              <Input value={draft.search} onChange={(event) => setDraft({ ...draft, search: event.target.value })}
                maxLength={255} autoComplete="off" />
            </FormField>
            <FormField label={t("platformRegistry.accountStatus")}>
              <Select value={draft.active} onChange={(event) => setDraft({ ...draft, active: event.target.value as PlatformUserFilters["active"] })}>
                <option value="">{t("platformAdmin.allStatuses")}</option>
                <option value="true">{t("platformRegistry.userEnabled")}</option>
                <option value="false">{t("platformRegistry.userDisabled")}</option>
              </Select>
            </FormField>
            <div className="flex flex-wrap gap-2">
              <Button type="submit"><Search className="size-4" aria-hidden="true" />{t("platformRegistry.find")}</Button>
              {filters.search || filters.active || filters.segment || draft.search || draft.active ? (
                <Button type="button" variant="ghost" onClick={clearFilters}>{t("platformAdmin.reset")}</Button>
              ) : null}
            </div>
          </form>
        </div>
        {directory.isPending ? <LoadingSkeleton title={t("platformRegistry.loading")} rows={3} /> : null}
        {directory.error ? <PlatformProblem message="error" retry={() => void directory.refetch()} /> : null}
        {results?.items.length ? (
          <>
            <div className="hidden lg:block">
              <DataTable>
                <table aria-label={t("platformRegistry.users")} className="w-full table-fixed text-left text-sm">
                  <thead className="border-b border-border-subtle bg-surface-2 text-xs text-text-secondary">
                    <tr>
                      <th scope="col" className="w-[31%] px-4 py-3">{t("platformRegistry.account")}</th>
                      <th scope="col" className="w-[22%] px-3 py-3">{t("platformRegistry.accountStatus")}</th>
                      <th scope="col" className="w-[14%] px-3 py-3">{t("platformRegistry.ownedWorkspaces")}</th>
                      <th scope="col" className="px-3 py-3">{t("platformRegistry.lastLogin")}</th>
                      <th scope="col" className="w-24"><span className="sr-only">{t("platformAdmin.details")}</span></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle">
                    {results.items.map((user) => (
                      <tr key={user.id} className="hover:bg-surface-2 focus-within:bg-surface-2">
                        <th scope="row" className="px-4 py-3.5">
                          <div className="flex min-w-0 items-center gap-3">
                            <AccountAvatar user={user} />
                            <div className="min-w-0">
                              <p className="break-words font-semibold">{userName(user)}</p>
                              <p className="mt-0.5 break-all text-xs font-normal text-text-secondary">{user.email}</p>
                            </div>
                          </div>
                        </th>
                        <td className="px-3 py-3.5"><div className="flex flex-wrap gap-1.5"><AccountStatus user={user} /><AccountSegment user={user} /></div></td>
                        <td className="px-3 py-3.5 tabular-nums">{number.format(user.owned_workspace_count)}</td>
                        <td className="px-3 py-3.5 text-xs text-text-secondary">{user.last_login_at ? date.format(new Date(user.last_login_at)) : t("platformRegistry.noLogin")}</td>
                        <td className="px-1 py-3.5 text-right">{openProfile(user)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </DataTable>
            </div>
            <ul aria-label={t("platformRegistry.users")} className="grid gap-2.5 lg:hidden">
              {results.items.map((user) => (
                <li key={user.id}>
                  <Card className="grid gap-3 shadow-none">
                    <div className="flex min-w-0 items-center gap-3">
                      <AccountAvatar user={user} />
                      <div className="min-w-0">
                        <p className="break-words font-semibold">{userName(user)}</p>
                        <p className="break-all text-xs text-text-secondary">{user.email}</p>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-1.5"><AccountStatus user={user} /><AccountSegment user={user} /></div>
                    <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border-subtle pt-2">
                      <dl className="text-xs text-text-secondary">
                        <div className="flex gap-1.5"><dt>{t("platformRegistry.ownedWorkspaces")}</dt><dd className="tabular-nums text-text-primary">{number.format(user.owned_workspace_count)}</dd></div>
                        <div className="mt-1 flex gap-1.5"><dt>{t("platformRegistry.lastLogin")}</dt><dd className="text-text-primary">{user.last_login_at ? date.format(new Date(user.last_login_at)) : t("platformRegistry.noLogin")}</dd></div>
                      </dl>
                      {openProfile(user)}
                    </div>
                  </Card>
                </li>
              ))}
            </ul>
          </>
        ) : results ? <EmptyState title={t("platformRegistry.empty")} description={t("platformRegistry.emptyDescription")} /> : null}
        {!directory.error ? <RegistryPagination page={cursors.length} nextCursor={results?.next_cursor}
          onPrevious={() => setCursors((values) => values.slice(0, -1))}
          onNext={(next) => setCursors((values) => [...values, next])} /> : null}
      </div>
      {selected ? <UserProfile key={selected} userId={selected} operatorId={operatorId} close={close}
        recheckAccess={recheckAccess} onOpenWorkspace={onOpenWorkspace} /> : null}
    </section>
  );
}
