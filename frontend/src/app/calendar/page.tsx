"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, CalendarCheck2, CheckCircle2, ChevronLeft, ChevronRight, ClipboardList, Plus, CalendarDays, TrendingUp } from "lucide-react";

import { WorkspaceHeader, WorkspacePage } from "@/components/crm-workspace";
import { MemoEditor } from "@/components/memo-editor";
import { Button } from "@/components/ui/primitives";
import { EmptyState, LoadingSkeleton } from "@/components/ui/states";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { dateLabel, kyivDateKey, localDayKey, monthKey } from "@/lib/planner-dates";
import { fetchOrders } from "@/services/orders";
import { fetchShipments } from "@/services/shipments";
import { createWorkspaceMemo, fetchWorkspaceMemos, updateWorkspaceMemo } from "@/services/workspace-memos";
import { WorkspaceMemoCreate } from "@/types/workspace-memo";

type CalendarEvent = { id: string; date: string; type: "task" | "order" | "shipped" | "delivered"; title: string; detail: string; href: string; done?: boolean };
const kinds = ["task", "order", "shipped", "delivered"] as const;
const dotClass: Record<CalendarEvent["type"], string> = {
  task: "bg-primary", order: "bg-info", shipped: "bg-warning", delivered: "bg-success",
};

function shiftMonth(value: string, amount: number) {
  const [year, month] = value.split("-").map(Number);
  const day = new Date(Date.UTC(year, month - 1 + amount, 1, 12));
  return monthKey(day.getUTCFullYear(), day.getUTCMonth());
}

export default function CalendarPage() {
  const { t, locale, formatStatus } = useI18n();
  const { currentWorkspaceId, currentWorkspace, status } = useAuth();
  const queryClient = useQueryClient();
  const workspaceId = currentWorkspaceId ?? "";
  const enabled = status === "authenticated" && !!workspaceId;
  const canEdit = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";
  const today = kyivDateKey();
  const [shownMonth, setShownMonth] = useState(() => today.slice(0, 7));
  const [selected, setSelected] = useState(today);
  const [editorOpen, setEditorOpen] = useState(false);
  const [visibleTypes, setVisibleTypes] = useState<CalendarEvent["type"][]>([...kinds]);

  useEffect(() => { setEditorOpen(false); setSelected(kyivDateKey()); setShownMonth(kyivDateKey().slice(0, 7)); }, [workspaceId]);

  const memos = useQuery({ queryKey: ["workspace-memos", workspaceId], queryFn: () => fetchWorkspaceMemos(workspaceId), enabled });
  const orders = useQuery({ queryKey: ["calendar-orders", workspaceId], queryFn: () => fetchOrders(workspaceId, ""), enabled });
  const shipments = useQuery({ queryKey: ["calendar-shipments", workspaceId], queryFn: () => fetchShipments(workspaceId), enabled });
  const createTask = useMutation({
    mutationFn: (payload: WorkspaceMemoCreate) => createWorkspaceMemo(workspaceId, payload),
    onSuccess: () => { setEditorOpen(false); void queryClient.invalidateQueries({ queryKey: ["workspace-memos", workspaceId] }); },
  });
  const completeTask = useMutation({
    mutationFn: ({ id, is_done }: { id: string; is_done: boolean }) => updateWorkspaceMemo(workspaceId, id, { is_done }),
    onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ["workspace-memos", workspaceId] }); },
  });

  const events = useMemo<CalendarEvent[]>(() => {
    const result: CalendarEvent[] = [];
    for (const memo of memos.data ?? []) {
      if (memo.kind === "TASK" && memo.due_on) {
        result.push({ id: memo.id, date: memo.due_on, type: "task", title: memo.title, detail: memo.body, href: "/notes", done: memo.is_done });
      }
    }
    for (const order of orders.data ?? []) {
      if (!order.created_at) continue;
      result.push({
        id: `order-${order.id}`, date: localDayKey(order.created_at), type: "order",
        title: t("planner.orderCreated", { number: order.order_number }), detail: formatStatus("orders", order.status), href: "/orders",
      });
    }
    for (const shipment of shipments.data ?? []) {
      const display = shipment.order_number ?? shipment.tracking_number ?? "";
      if (shipment.shipped_at) result.push({ id: `shipped-${shipment.id}`, date: localDayKey(shipment.shipped_at), type: "shipped", title: t("planner.shipped", { number: display }), detail: formatStatus("shipments", shipment.status), href: "/shipments" });
      if (shipment.delivered_at) result.push({ id: `delivered-${shipment.id}`, date: localDayKey(shipment.delivered_at), type: "delivered", title: t("planner.delivered", { number: display }), detail: formatStatus("shipments", shipment.status), href: "/shipments" });
    }
    return result;
  }, [memos.data, orders.data, shipments.data, t, formatStatus]);

  const filtered = useMemo(() => events.filter((item) => visibleTypes.includes(item.type)), [events, visibleTypes]);
  const byDay = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    for (const event of filtered) map.set(event.date, [...(map.get(event.date) ?? []), event]);
    return map;
  }, [filtered]);
  const [y, m] = shownMonth.split("-").map(Number);
  const first = new Date(Date.UTC(y, m - 1, 1, 12));
  const leading = (first.getUTCDay() + 6) % 7;
  const monthDays = new Date(Date.UTC(y, m, 0, 12)).getUTCDate();
  const cellCount = Math.ceil((leading + monthDays) / 7) * 7;
  const cells = Array.from({ length: cellCount }, (_, index) => {
    const cellDate = new Date(Date.UTC(y, m - 1, index - leading + 1, 12));
    return cellDate.toISOString().slice(0, 10);
  });
  const selectedEvents = (byDay.get(selected) ?? []).sort((a, b) => kinds.indexOf(a.type) - kinds.indexOf(b.type));
  const monthEvents = filtered.filter((item) => item.date.startsWith(shownMonth));
  const currentTasks = monthEvents.filter((item) => item.type === "task" && !item.done).length;
  const daysWithEvents = new Set(monthEvents.map((item) => item.date)).size;
  const monthLabel = dateLabel(`${shownMonth}-01`, locale, { month: "long", year: "numeric" });
  const loading = memos.isLoading || orders.isLoading || shipments.isLoading;

  function move(amount: number) {
    const next = shiftMonth(shownMonth, amount);
    setShownMonth(next);
    setSelected(`${next}-01`);
  }
  function jumpToday() { setShownMonth(today.slice(0, 7)); setSelected(today); }
  function toggleType(type: CalendarEvent["type"]) {
    setVisibleTypes((prev) => prev.includes(type) ? prev.filter((item) => item !== type) : [...prev, type]);
  }

  return <WorkspacePage className="lg:!px-7 lg:!py-7 2xl:!px-9">
    <WorkspaceHeader title={t("navigation.calendar")} description={t("planner.calendarSubtitle")} actions={
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={jumpToday}>{t("planner.today")}</Button>
        {canEdit ? <Button onClick={() => { createTask.reset(); setEditorOpen(true); }}><Plus className="h-4 w-4" />{t("planner.newTask")}</Button> : null}
      </div>
    } />

    <div className="hidden min-w-0 gap-3 lg:grid lg:grid-cols-3" data-planner-desktop-summary>
      <div className="relative overflow-hidden rounded-[22px] border border-primary/20 bg-gradient-to-br from-primary/15 via-surface-1 to-surface-1 p-5">
        <CalendarDays className="absolute right-4 top-4 h-10 w-10 text-primary/20" aria-hidden="true" />
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">{t("planner.monthEvents", { count: monthEvents.length })}</p>
        <p className="mt-3 text-3xl font-bold tabular-nums text-text-primary">{loading ? "—" : monthEvents.length}</p>
        <p className="mt-1 text-xs text-text-secondary">{monthLabel}</p>
      </div>
      <div className="relative overflow-hidden rounded-[22px] border border-border-subtle bg-surface-1 p-5">
        <ClipboardList className="absolute right-4 top-4 h-10 w-10 text-primary/15" aria-hidden="true" />
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">{t("planner.desktopOpenTasks")}</p>
        <p className="mt-3 text-3xl font-bold tabular-nums text-text-primary">{loading ? "—" : currentTasks}</p>
        <p className="mt-1 text-xs text-text-secondary">{t("planner.desktopOpenTasksHint")}</p>
      </div>
      <div className="relative overflow-hidden rounded-[22px] border border-border-subtle bg-surface-1 p-5">
        <TrendingUp className="absolute right-4 top-4 h-10 w-10 text-success/15" aria-hidden="true" />
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">{t("planner.desktopActiveDays")}</p>
        <p className="mt-3 text-3xl font-bold tabular-nums text-text-primary">{loading ? "—" : daysWithEvents}</p>
        <p className="mt-1 text-xs text-text-secondary">{t("planner.desktopActiveDaysHint")}</p>
      </div>
    </div>

    {editorOpen && canEdit ? <MemoEditor key={selected} kind="TASK" initialDueOn={selected} saving={createTask.isPending} error={createTask.isError ? t("planner.saveError") : null} onSave={(payload) => createTask.mutate(payload)} onCancel={() => setEditorOpen(false)} /> : null}

    <section className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(320px,360px)] lg:items-start xl:gap-5">
      <div className="min-w-0 rounded-3xl border border-border-subtle bg-surface-1 p-3 shadow-[var(--shadow-card)] sm:p-5 lg:p-6 lg:ring-1 lg:ring-white/[0.02]" data-planner-calendar>
        <div className="flex items-center justify-between gap-3 px-1 py-1">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold capitalize text-text-primary">{monthLabel}</h2>
            <p className="mt-1 text-xs text-text-muted">{t("planner.monthEvents", { count: monthEvents.length })}</p>
          </div>
          <div className="flex gap-1">
            <button type="button" onClick={() => move(-1)} aria-label={t("planner.prevMonth")} className="grid h-11 w-11 place-items-center rounded-xl text-text-secondary transition hover:bg-surface-hover"><ChevronLeft className="h-5 w-5" /></button>
            <button type="button" onClick={() => move(1)} aria-label={t("planner.nextMonth")} className="grid h-11 w-11 place-items-center rounded-xl text-text-secondary transition hover:bg-surface-hover"><ChevronRight className="h-5 w-5" /></button>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-7 gap-1 sm:gap-1.5 lg:gap-1" role="grid" aria-label={monthLabel}>
          {Array.from({ length: 7 }, (_, index) => <div key={index} className="pb-2 text-center text-[11px] font-semibold uppercase text-text-muted lg:border-b lg:border-border-subtle lg:pb-3 lg:tracking-[0.15em]" role="columnheader">{t(`planner.week.${index}`)}</div>)}
          {cells.map((day) => {
            const within = day.startsWith(shownMonth);
            const items = byDay.get(day) ?? [];
            return <button type="button" key={day} onClick={() => { setSelected(day); if (!within) setShownMonth(day.slice(0, 7)); }} role="gridcell" aria-selected={selected === day}
              aria-label={`${dateLabel(day, locale, { day: "numeric", month: "long", year: "numeric" })}: ${items.length}`}
              className={`group relative flex min-h-12 min-w-0 flex-col items-center justify-center gap-1 rounded-xl border text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring sm:min-h-16 lg:min-h-[100px] lg:items-stretch lg:justify-start lg:gap-2 lg:rounded-2xl lg:p-2 2xl:min-h-[110px] ${selected === day ? "border-primary bg-primary/15 text-primary lg:shadow-[inset_0_0_0_1px_var(--primary)]" : "border-transparent hover:border-border-subtle hover:bg-surface-hover lg:border-border-subtle/60 lg:bg-surface-2/35"} ${within ? "text-text-primary" : "text-text-muted/50 lg:opacity-50"}`}>
              <span className={`${day === today ? "grid h-7 w-7 place-items-center rounded-full bg-primary text-primary-foreground" : ""} lg:!mx-0 lg:text-sm lg:font-bold`}>{Number(day.slice(-2))}</span>
              <span className="flex h-1.5 items-center gap-0.5" aria-hidden="true">{Array.from(new Set(items.map((item) => item.type))).slice(0, 3).map(kind => <span key={kind} className={`h-1.5 w-1.5 rounded-full ${dotClass[kind]}`} />)}</span>
              <span className="hidden min-w-0 space-y-1 lg:block" aria-hidden="true">
                {kinds.filter(kind => items.some(event => event.type === kind)).slice(0, 3).map(kind => (
                  <span key={kind} className={`flex min-w-0 items-center gap-1.5 rounded-md bg-surface-1/75 px-1.5 py-1 text-left text-[10px] font-semibold leading-4 ${kind === "task" ? "text-primary" : kind === "order" ? "text-info" : kind === "shipped" ? "text-warning" : "text-success"}`}>
                    <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${dotClass[kind]}`} />
                    <span className="truncate">{t(`planner.event.${kind}`)}</span>
                    <span className="ml-auto shrink-0 font-bold tabular-nums">{items.filter(event => event.type === kind).length}</span>
                  </span>
                ))}
                {kinds.filter(kind => items.some(event => event.type === kind)).length > 3 ? <span className="block text-left text-[10px] font-semibold text-text-muted">{t("planner.desktopMoreCategories")}</span> : null}
              </span>
            </button>;
          })}
        </div>
        <div className="mt-4 flex flex-wrap gap-2 border-t border-border-subtle pt-4" role="group" aria-label={t("planner.eventsFilter")}>
          {kinds.map(type => <button key={type} type="button" aria-pressed={visibleTypes.includes(type)} onClick={() => toggleType(type)} className={`flex min-h-9 items-center gap-2 rounded-full border px-3 text-xs font-medium transition ${visibleTypes.includes(type) ? "border-border-strong bg-surface-2 text-text-primary" : "border-border-subtle text-text-muted opacity-60"}`}><span className={`h-2 w-2 rounded-full ${dotClass[type]}`} />{t(`planner.event.${type}`)}</button>)}
        </div>
      </div>

      <aside className="min-w-0 rounded-3xl border border-border-subtle bg-surface-1 p-4 shadow-[var(--shadow-card)] sm:p-5 lg:sticky lg:top-5 lg:border-primary/15 lg:p-6 lg:shadow-[var(--shadow-card)]">
        <div className="hidden items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-primary lg:flex"><span className="h-2 w-2 rounded-full bg-primary" />{t("planner.desktopDayAgenda")}</div>
        <h2 className="text-base font-semibold text-text-primary lg:mt-3 lg:text-xl">{dateLabel(selected, locale, { weekday: "long", day: "numeric", month: "long" })}</h2>
        <p className="mt-1 text-xs text-text-muted">{t("planner.dayEvents", { count: selectedEvents.length })}</p>
        {loading ? <div className="mt-4"><LoadingSkeleton rows={2} /></div> : null}
        {(memos.isError || orders.isError || shipments.isError) ? <p role="alert" className="mt-3 text-xs text-danger">{t("planner.partialLoad")}</p> : null}
        {!loading && selectedEvents.length === 0 ? <div className="mt-5"><EmptyState title={t("planner.emptyDay")} description={t("planner.emptyDayHint")} /></div> : null}
        {!loading && selectedEvents.length > 0 ? <div className="mt-4 grid gap-2">
          {selectedEvents.map(event => <div key={event.id} className="flex items-start gap-3 rounded-2xl border border-border-subtle bg-surface-2 p-3 lg:transition lg:duration-200 lg:hover:-translate-y-0.5 lg:hover:border-primary/30 lg:hover:shadow-[var(--shadow-card)]">
            <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${dotClass[event.type]}`} />
            <div className="min-w-0 flex-1">
              <p className={`break-words text-sm font-semibold text-text-primary ${event.done ? "line-through opacity-65" : ""}`}>{event.title}</p>
              <p className="mt-1 text-xs text-text-muted">{t(`planner.event.${event.type}`)}</p>
              {event.detail ? <p className="mt-1 line-clamp-2 break-words text-xs text-text-secondary">{event.detail}</p> : null}
              <Link href={event.href} className="mt-2 inline-flex min-h-8 items-center gap-1 text-xs font-medium text-primary hover:underline">{t("planner.viewDetails")}<ArrowRight className="h-3.5 w-3.5" /></Link>
            </div>
            {canEdit && event.type === "task" ? <button type="button" disabled={completeTask.isPending} onClick={() => completeTask.mutate({ id: event.id, is_done: !event.done })} aria-label={event.done ? t("planner.reopen") : t("planner.complete")} className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-surface-1 text-text-secondary hover:text-primary">{event.done ? <CheckCircle2 className="h-5 w-5 text-success" /> : <CalendarCheck2 className="h-5 w-5" />}</button> : null}
          </div>)}
        </div> : null}
        <p className="mt-4 text-xs leading-5 text-text-muted">{t("planner.calendarFactNote")}</p>
        <Link href="/notes" className="mt-3 inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-primary hover:underline"><ClipboardList className="h-4 w-4" />{t("planner.openNotes")}</Link>
      </aside>
    </section>
  </WorkspacePage>;
}
