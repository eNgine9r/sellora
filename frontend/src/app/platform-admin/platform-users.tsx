"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Drawer } from "@/components/ui/overlay";
import { Button, Card, Checkbox, EmptyState, FormField, Input, LoadingSkeleton, StatusBadge } from "@/components/ui/primitives";
import { useI18n } from "@/i18n/provider";
import { ApiError } from "@/services/api";
import { platformAdminApi, type PlatformUser } from "@/services/platform-admin";
import { accessDenied, PlatformProblem } from "./platform-feedback";

const defaultFilters = { search: "", withoutWorkspaces: false };

function userName(user: PlatformUser) {
  return [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email;
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
          <Card>
            <p className="break-all text-sm text-text-secondary">{user.email}</p>
            <p className="mt-2 text-xs text-text-secondary">{t("platformRegistry.created", { time: date.format(new Date(user.created_at)) })}</p>
            <div className="mt-3">
              <StatusBadge tone={user.is_active ? "success" : "neutral"}>
                {t(user.is_active ? "platformRegistry.userEnabled" : "platformRegistry.userDisabled")}
              </StatusBadge>
            </div>
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
  const [enabled, setEnabled] = useState(false);
  const [draft, setDraft] = useState(defaultFilters);
  const [filters, setFilters] = useState(defaultFilters);
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const [selected, setSelected] = useState<string | null>(null);
  const close = useCallback(() => setSelected(null), []);
  const cursor = cursors[cursors.length - 1];
  const directory = useQuery({
    queryKey: ["platform-admin", operatorId, "users", filters, cursor],
    queryFn: ({ signal }) => platformAdminApi.users(filters.search, filters.withoutWorkspaces, cursor, signal),
    enabled, retry: false, gcTime: 0,
  });
  const denied = accessDenied(directory.error);
  useEffect(() => { if (denied) recheckAccess(); }, [denied, recheckAccess]);

  function submit(event: FormEvent) {
    event.preventDefault();
    setCursors([null]);
    setFilters({ ...draft, search: draft.search.trim() });
    setEnabled(true);
  }

  const date = new Intl.DateTimeFormat(locale, { dateStyle: "medium" });
  const results = directory.error ? undefined : directory.data;

  return (
    <section id="platform-users" className="grid min-w-0 scroll-mt-32 gap-4 xl:scroll-mt-8" aria-labelledby="platform-users-title" tabIndex={-1}>
      <div>
        <h2 id="platform-users-title" className="text-xl font-bold tracking-tight sm:text-2xl">{t("platformRegistry.users")}</h2>
        <p className="mt-1 text-sm text-text-secondary">{t("platformRegistry.description")}</p>
      </div>
      <form onSubmit={submit} className="grid gap-3 rounded-[var(--radius-card)] border border-border-subtle bg-surface-1 p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
        <FormField label={t("platformRegistry.search")}>
          <Input value={draft.search} onChange={(event) => setDraft({ ...draft, search: event.target.value })} maxLength={255} autoComplete="off" />
        </FormField>
        <Button type="submit" variant="brand"><Search className="size-4" aria-hidden="true" />{t(enabled ? "platformAdmin.applyFilters" : "platformRegistry.load")}</Button>
        <label className="flex items-center gap-2 text-sm text-text-secondary sm:col-span-2">
          <Checkbox checked={draft.withoutWorkspaces} onChange={(event) => setDraft({ ...draft, withoutWorkspaces: event.target.checked })} />
          {t("platformRegistry.withoutWorkspaces")}
        </label>
      </form>
      {enabled && directory.isPending ? <LoadingSkeleton title={t("common.loading")} rows={2} /> : null}
      {directory.error ? <PlatformProblem message={denied ? "forbidden" : "error"} retry={denied ? undefined : () => void directory.refetch()} /> : null}
      {results?.items.length ? (
        <Card className="py-0 sm:py-0">
          <ul aria-label={t("platformRegistry.users")} className="divide-y divide-border-subtle">
            {results.items.map((user) => (
              <li className="flex flex-wrap items-center justify-between gap-2 py-3" key={user.id}>
                <div className="min-w-0">
                  <p className="break-words font-semibold">{userName(user)}</p>
                  <p className="break-all text-xs text-text-secondary">{user.email} · {date.format(new Date(user.created_at))}</p>
                </div>
                <Button variant="ghost" size="sm" aria-label={t("platformRegistry.openUser", { name: userName(user) })} onClick={() => setSelected(user.id)}>
                  {t("platformAdmin.details")}<ArrowUpRight className="size-4 text-violet-300" aria-hidden="true" />
                </Button>
              </li>
            ))}
          </ul>
        </Card>
      ) : results ? <EmptyState title={t("platformRegistry.empty")} description={t("platformRegistry.emptyDescription")} /> : null}
      {!directory.error ? <RegistryPagination page={cursors.length} nextCursor={results?.next_cursor}
        onPrevious={() => setCursors((values) => values.slice(0, -1))}
        onNext={(next) => setCursors((values) => [...values, next])} /> : null}
      {selected ? <UserProfile key={selected} userId={selected} operatorId={operatorId} close={close}
        recheckAccess={recheckAccess} onOpenWorkspace={onOpenWorkspace} /> : null}
    </section>
  );
}
