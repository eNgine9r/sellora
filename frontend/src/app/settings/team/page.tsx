"use client";

import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UserPlus } from "lucide-react";
import { WorkspacePage, WorkspaceHeader, CompactSummary } from "@/components/crm-workspace";
import { Card, FormField, Input, Select, Button, StatusBadge, DataTable } from "@/components/ui/primitives";
import { ConfirmationDialog, Modal } from "@/components/ui/overlay";
import { EmptyState, LoadingSkeleton } from "@/components/ui/states";
import { PaginationControls } from "@/components/pagination-controls";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { safeApiErrorMessage } from "@/services/api";
import { addWorkspaceUser, deactivateWorkspaceUser, fetchWorkspaceUsers, updateWorkspaceUserRole, WorkspaceRole, WorkspaceUser } from "@/services/workspaces";

const roles: WorkspaceRole[] = ["OWNER", "MANAGER", "ANALYST"];
const pageSize = 10;

export default function TeamPage() {
  const { t } = useI18n();
  const { currentWorkspaceId, currentWorkspace, currentUser } = useAuth();
  const queryClient = useQueryClient();
  const workspaceId = currentWorkspaceId ?? "";
  const canManage = currentWorkspace?.role === "OWNER";
  const [modalOpen, setModalOpen] = useState(false);
  const [pendingDeactivate, setPendingDeactivate] = useState<WorkspaceUser | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [form, setForm] = useState({ full_name: "", email: "", role: "MANAGER" as WorkspaceRole, temporary_password: "" });
  const users = useQuery({ queryKey: ["workspace-users", workspaceId], queryFn: () => fetchWorkspaceUsers(workspaceId), enabled: Boolean(workspaceId) && canManage });
  const members = useMemo(() => users.data ?? [], [users.data]);
  const activeOwners = members.filter((user) => user.is_active && user.role === "OWNER").length;
  const activeCount = members.filter((user) => user.is_active).length;
  const visibleMembers = useMemo(() => members.slice((page - 1) * pageSize, page * pageSize), [members, page]);
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["workspace-users", workspaceId] });
  const addUser = useMutation({ mutationFn: () => addWorkspaceUser(workspaceId, form), onSuccess: async () => { setModalOpen(false); setForm({ full_name: "", email: "", role: "MANAGER", temporary_password: "" }); setMessage(t("settings.teamPage.added")); await invalidate(); }, onError: (error) => setMessage(safeApiErrorMessage(error, t("settings.teamPage.addFailed"))) });
  const roleChange = useMutation({ mutationFn: ({ userId, role }: { userId: string; role: WorkspaceRole }) => updateWorkspaceUserRole(workspaceId, userId, role), onSuccess: async () => { setMessage(t("settings.teamPage.roleSaved")); await invalidate(); }, onError: (error) => setMessage(safeApiErrorMessage(error, t("settings.teamPage.roleFailed"))) });
  const deactivate = useMutation({ mutationFn: (userId: string) => deactivateWorkspaceUser(workspaceId, userId), onSuccess: async () => { setPendingDeactivate(null); setMessage(t("settings.teamPage.deactivated")); await invalidate(); }, onError: (error) => setMessage(safeApiErrorMessage(error, t("settings.teamPage.deactivateFailed"))) });
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (!canManage) return; addUser.mutate(); }
  function isLastOwner(user: WorkspaceUser) { return user.is_active && user.role === "OWNER" && activeOwners <= 1; }
  function isCurrentUser(user: WorkspaceUser) { return user.email === currentUser?.email || user.user_id === currentUser?.id; }

  return <WorkspacePage>
    <WorkspaceHeader eyebrow={t("settings.label")} title={t("settings.teamPage.title")} description={t("settings.teamPage.description")} actions={canManage ? <Button onClick={() => setModalOpen(true)}><UserPlus className="h-4 w-4" />{t("settings.teamPage.addAction")}</Button> : <StatusBadge tone="warning">{t("settings.ownerOnly")}</StatusBadge>} />
    {canManage ? <CompactSummary items={[{ label: t("settings.teamPage.summaryActive"), value: activeCount, helper: t("settings.teamPage.summaryActiveHelp") }, { label: t("settings.teamPage.summaryInactive"), value: members.length - activeCount, helper: t("settings.teamPage.summaryInactiveHelp") }, { label: t("settings.teamPage.summaryOwners"), value: activeOwners, helper: t("settings.teamPage.summaryOwnersHelp") }, { label: t("settings.teamPage.summaryRoles"), value: "3", helper: t("settings.teamPage.summaryRolesHelp") }]} /> : null}
    {!canManage ? <Card><p className="text-sm font-bold text-text-secondary">{t("settings.teamPage.restricted")}</p></Card> : null}
    {message ? <p className="rounded-2xl border border-info/25 bg-[var(--info-surface)] p-3 text-sm font-bold text-[var(--info-foreground)]">{message}</p> : null}
    {users.isLoading ? <LoadingSkeleton rows={4} title={t("settings.teamPage.loading")} /> : null}
    {canManage && !users.isLoading && members.length === 0 ? <EmptyState title={t("settings.teamPage.emptyTitle")} description={t("settings.teamPage.emptyDescription")} /> : null}
    {canManage && members.length > 0 ? <section className="grid gap-3">
      <DataTable><table className="hidden min-w-full text-left text-sm lg:table"><thead className="border-b border-border-subtle bg-surface-2 text-xs font-black uppercase tracking-[0.12em] text-text-muted"><tr><th className="px-4 py-3">{t("settings.teamPage.userColumn")}</th><th className="px-4 py-3">{t("settings.teamPage.emailColumn")}</th><th className="px-4 py-3">{t("settings.teamPage.roleColumn")}</th><th className="px-4 py-3">{t("settings.teamPage.statusColumn")}</th><th className="px-4 py-3 text-right">{t("settings.teamPage.actionsColumn")}</th></tr></thead><tbody className="divide-y divide-border-subtle">{visibleMembers.map((user) => <MemberRow key={user.user_id} user={user} lastOwner={isLastOwner(user)} current={isCurrentUser(user)} canMutate={canManage} onRole={(role) => roleChange.mutate({ userId: user.user_id, role })} onDeactivate={() => setPendingDeactivate(user)} rolePending={roleChange.isPending} />)}</tbody></table><div className="grid gap-3 p-3 lg:hidden">{visibleMembers.map((user) => <MemberCard key={user.user_id} user={user} lastOwner={isLastOwner(user)} current={isCurrentUser(user)} onRole={(role) => roleChange.mutate({ userId: user.user_id, role })} onDeactivate={() => setPendingDeactivate(user)} rolePending={roleChange.isPending} />)}</div></DataTable>
      <PaginationControls page={page} pageSize={pageSize} totalItems={members.length} onPageChange={setPage} onPageSizeChange={() => undefined} />
    </section> : null}
    <Modal open={modalOpen} title={t("settings.teamPage.addTitle")} description={t("settings.teamPage.addDescription")} onClose={() => setModalOpen(false)}><form className="grid gap-4" onSubmit={submit}><FormField label={t("settings.teamPage.nameLabel")}><Input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required /></FormField><FormField label={t("settings.teamPage.emailLabel")}><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required /></FormField><FormField label={t("settings.teamPage.roleLabel")} hint={t("settings.teamPage.roleHint")}><Select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as WorkspaceRole })}>{roles.map((role) => <option key={role} value={role}>{t(`roles.${role}`)}</option>)}</Select></FormField><FormField label={t("settings.teamPage.tempPasswordLabel")} hint={t("settings.teamPage.tempPasswordHint")}><Input type="password" minLength={8} autoComplete="new-password" value={form.temporary_password} onChange={(e) => setForm({ ...form, temporary_password: e.target.value })} required /></FormField><div className="grid gap-3 sm:grid-cols-2"><Button type="button" variant="secondary" onClick={() => setModalOpen(false)} disabled={addUser.isPending}>{t("actions.cancel")}</Button><Button type="submit" loading={addUser.isPending}>{t("settings.teamPage.addSubmit")}</Button></div></form></Modal>
    <ConfirmationDialog open={Boolean(pendingDeactivate)} title={t("settings.teamPage.deactivateTitle")} description={t("settings.teamPage.deactivateDescription", { email: pendingDeactivate?.email ?? "" })} actionLabel={t("settings.teamPage.deactivateAction")} isSubmitting={deactivate.isPending} onCancel={() => setPendingDeactivate(null)} onConfirm={() => pendingDeactivate ? deactivate.mutate(pendingDeactivate.user_id) : undefined} />
  </WorkspacePage>;
}

function MemberRow({ user, lastOwner, current, canMutate, rolePending, onRole, onDeactivate }: { user: WorkspaceUser; lastOwner: boolean; current: boolean; canMutate: boolean; rolePending: boolean; onRole: (role: WorkspaceRole) => void; onDeactivate: () => void }) {
  const { t } = useI18n();
  return <tr className="hover:bg-surface-hover"><td className="px-4 py-3"><p className="font-black text-text-primary">{user.full_name}</p>{current ? <p className="text-xs font-bold text-primary">{t("settings.teamPage.currentUser")}</p> : null}</td><td className="max-w-xs truncate px-4 py-3 text-text-secondary">{user.email}</td><td className="px-4 py-3"><Select value={user.role} disabled={!canMutate || !user.is_active || lastOwner || rolePending} onChange={(e) => onRole(e.target.value as WorkspaceRole)}>{roles.map((role) => <option key={role} value={role}>{t(`roles.${role}`)}</option>)}</Select></td><td className="px-4 py-3"><StatusBadge tone={user.is_active ? "success" : "neutral"}>{user.is_active ? t("settings.teamPage.active") : t("settings.teamPage.inactive")}</StatusBadge></td><td className="px-4 py-3 text-right"><Button variant="danger" size="sm" disabled={!user.is_active || lastOwner || current} onClick={onDeactivate}>{t("settings.teamPage.deactivateAction")}</Button>{lastOwner ? <p className="mt-1 text-xs font-bold text-[var(--warning-foreground)]">{t("settings.teamPage.lastOwnerGuard")}</p> : null}</td></tr>;
}
function MemberCard({ user, lastOwner, current, rolePending, onRole, onDeactivate }: { user: WorkspaceUser; lastOwner: boolean; current: boolean; rolePending: boolean; onRole: (role: WorkspaceRole) => void; onDeactivate: () => void }) {
  const { t } = useI18n();
  return <article className="rounded-3xl border border-border-subtle bg-surface-1 p-4"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><p className="font-black text-text-primary">{user.full_name}</p><p className="truncate text-sm text-text-secondary">{user.email}</p>{current ? <p className="mt-1 text-xs font-bold text-primary">{t("settings.teamPage.currentUser")}</p> : null}</div><StatusBadge tone={user.is_active ? "success" : "neutral"}>{user.is_active ? t("settings.teamPage.active") : t("settings.teamPage.inactive")}</StatusBadge></div><div className="mt-4 grid gap-3"><Select value={user.role} disabled={!user.is_active || lastOwner || rolePending} onChange={(e) => onRole(e.target.value as WorkspaceRole)}>{roles.map((role) => <option key={role} value={role}>{t(`roles.${role}`)}</option>)}</Select><Button variant="danger" size="sm" disabled={!user.is_active || lastOwner || current} onClick={onDeactivate}>{t("settings.teamPage.deactivateAction")}</Button>{lastOwner ? <p className="text-xs font-bold text-[var(--warning-foreground)]">{t("settings.teamPage.lastOwnerGuard")}</p> : null}</div></article>;
}
