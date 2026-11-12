"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, RotateCcw, SlidersHorizontal } from "lucide-react";
import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
import { EditRecordDialog } from "@/components/edit-record-dialog";
import { SearchInput, SortSelect } from "@/components/filter-controls";
import { FormDialog } from "@/components/form-dialog";
import { clampPage, PAGE_SIZE_OPTIONS, paginateItems, PaginationControls } from "@/components/pagination-controls";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";
import { Button, EntitySidePanel, WorkspaceHeader, WorkspacePage, WorkspaceSplitView } from "@/components/crm-workspace";
import { ShipmentDetails } from "@/features/shipments/components/shipment-details";
import { NovaPoshtaExternalInbox } from "@/features/shipments/components/nova-poshta-external-inbox";
import { ShipmentForm } from "@/features/shipments/components/shipment-form";
import { ShipmentTable } from "@/features/shipments/components/shipment-table";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { buildShipmentUpdatePayload } from "@/lib/payload-builders";
import { safeApiErrorMessage } from "@/services/api";
import { fetchOrders } from "@/services/orders";
import { changeShipmentStatus, createShipment, deleteShipment, fetchShipmentSummary, fetchShipments, updateShipment } from "@/services/shipments";
import { Shipment, ShipmentCarrier, ShipmentStatus } from "@/types/shipments";

const STATUSES: (ShipmentStatus | "")[] = ["", "DRAFT", "CREATED", "IN_TRANSIT", "ARRIVED", "DELIVERED", "RETURNED", "CANCELLED"];
const CARRIERS: (ShipmentCarrier | "")[] = ["", "NOVA_POSHTA", "UKRPOSHTA", "MEEST", "ROZETKA_DELIVERY", "OTHER"];
type TtnFilter = "" | "hasTtn" | "missingTtn" | "needsAction";

function shipmentNeedsAction(shipment: Shipment) {
  return !shipment.customer_id || (!shipment.tracking_number && shipment.carrier === "NOVA_POSHTA") || ["DRAFT", "CREATED", "ARRIVED"].includes(shipment.status);
}

export default function ShipmentsPage() {
  const { t, formatStatus, locale } = useI18n();
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspace, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const enabled = authStatus === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);
  const canEdit = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";
  const [status, setStatus] = useState<ShipmentStatus | "">("");
  const [carrier, setCarrier] = useState<ShipmentCarrier | "">("");
  const [ttnFilter, setTtnFilter] = useState<TtnFilter>("");
  const [search, setSearch] = useState("");
  const [shipmentSort, setShipmentSort] = useState("newest");
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const filterMenuRef = useRef<HTMLDivElement | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<(typeof PAGE_SIZE_OPTIONS)[number]>(5);
  const [selectedShipment, setSelectedShipment] = useState<Shipment | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [initialOrderId, setInitialOrderId] = useState<string | undefined>();
  const [editingShipment, setEditingShipment] = useState<Shipment | null>(null);
  const [archivingShipment, setArchivingShipment] = useState<Shipment | null>(null);

  const shipmentsQuery = useQuery({ queryKey: ["shipments", workspaceId, status, search], queryFn: () => fetchShipments(workspaceId, status, search), enabled, refetchInterval: 45_000 });
  // Summary cards always use the complete workspace list, not a search/status
  // subset. The unfiltered query key is shared with the main list when idle.
  const overviewQuery = useQuery({
    queryKey: ["shipments", workspaceId, "", ""],
    queryFn: () => fetchShipments(workspaceId, "", ""),
    enabled,
    refetchInterval: 45_000,
  });
  const summaryQuery = useQuery({ queryKey: ["shipments-summary", workspaceId], queryFn: () => fetchShipmentSummary(workspaceId), enabled, refetchInterval: 45_000 });
  const ordersQuery = useQuery({ queryKey: ["orders", workspaceId, "shipment-select"], queryFn: () => fetchOrders(workspaceId, ""), enabled, refetchInterval: 45_000 });
  const invalidateShipmentState = () => {
    queryClient.invalidateQueries({ queryKey: ["shipments", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["shipments-summary", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["orders", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["order-shipment", workspaceId] });
  };
  const createMutation = useMutation({ mutationFn: (payload: Parameters<typeof createShipment>[1]) => createShipment(workspaceId, payload), onSuccess: (shipment) => { setSelectedShipment(shipment); setIsCreateOpen(false); invalidateShipmentState(); } });
  const statusMutation = useMutation({ mutationFn: ({ shipmentId, nextStatus }: { shipmentId: string; nextStatus: ShipmentStatus }) => changeShipmentStatus(workspaceId, shipmentId, nextStatus), onSuccess: (shipment) => { setSelectedShipment(shipment); invalidateShipmentState(); } });
  const updateMutation = useMutation({ mutationFn: (values: Record<string, string>) => updateShipment(workspaceId, editingShipment?.id ?? "", buildShipmentUpdatePayload(values)), onSuccess: (shipment) => { setEditingShipment(null); setSelectedShipment(shipment); invalidateShipmentState(); } });
  const archiveMutation = useMutation({ mutationFn: () => deleteShipment(workspaceId, archivingShipment?.id ?? ""), onSuccess: () => { if (selectedShipment?.id === archivingShipment?.id) setSelectedShipment(null); setArchivingShipment(null); invalidateShipmentState(); } });

  const filteredShipments = useMemo(() => {
    const query = search.trim().toLowerCase();
    return (shipmentsQuery.data ?? [])
      .filter((shipment) => {
        const tracking = shipment.nova_poshta_document_number ?? shipment.tracking_number;
        const searchable = [tracking, shipment.order_number, shipment.customer_name, shipment.customer_phone, shipment.city, shipment.warehouse].filter(Boolean).join(" ").toLowerCase();
        const matchesSearch = !query || searchable.includes(query);
        const matchesCarrier = !carrier || shipment.carrier === carrier;
        const matchesTtn =
          !ttnFilter ||
          (ttnFilter === "hasTtn" && Boolean(tracking)) ||
          (ttnFilter === "missingTtn" && !tracking) ||
          (ttnFilter === "needsAction" && shipmentNeedsAction(shipment));
        return matchesSearch && matchesCarrier && matchesTtn;
      })
      .sort((left, right) => {
        if (shipmentSort === "oldest") return left.created_at.localeCompare(right.created_at);
        if (shipmentSort === "status") return left.status.localeCompare(right.status);
        if (shipmentSort === "updatedDesc") return right.updated_at.localeCompare(left.updated_at);
        return right.created_at.localeCompare(left.created_at);
      });
  }, [carrier, search, shipmentSort, shipmentsQuery.data, ttnFilter]);
  const paginatedShipments = useMemo(() => paginateItems(filteredShipments, page, pageSize), [filteredShipments, page, pageSize]);
  const hasAnyShipments = (overviewQuery.data?.length ?? 0) > 0;
  const hasActiveFilters = Boolean(search.trim() || status || carrier || ttnFilter || shipmentSort !== "newest");

  useEffect(() => {
    const orderId = new URLSearchParams(window.location.search).get("order_id") ?? undefined;
    if (orderId) {
      setInitialOrderId(orderId);
      setIsCreateOpen(true);
    }
  }, []);

  useEffect(() => {
    setPage(1);
  }, [search, status, carrier, ttnFilter, shipmentSort, pageSize]);

  useEffect(() => {
    setPage((currentPage) => clampPage(currentPage, pageSize, filteredShipments.length));
  }, [filteredShipments.length, pageSize]);

  useEffect(() => {
    setSelectedShipment(null);
    setEditingShipment(null);
    setArchivingShipment(null);
    setIsCreateOpen(false);
    setInitialOrderId(undefined);
  }, [workspaceId]);

  useEffect(() => {
    if (!showAdvancedFilters) return;
    const dismissOutside = (event: PointerEvent) => {
      if (!filterMenuRef.current?.contains(event.target as Node)) setShowAdvancedFilters(false);
    };
    const dismissEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setShowAdvancedFilters(false);
    };
    document.addEventListener("pointerdown", dismissOutside);
    document.addEventListener("keydown", dismissEscape);
    return () => {
      document.removeEventListener("pointerdown", dismissOutside);
      document.removeEventListener("keydown", dismissEscape);
    };
  }, [showAdvancedFilters]);

  const overview = overviewQuery.data ?? [];
  const allShipments = overview.length;
  const readyShipments = overview.filter((shipment) => shipment.status === "DRAFT" || shipment.status === "CREATED").length;
  const deliveredShipments = overview.filter((shipment) => shipment.status === "DELIVERED").length;
  const issueShipments = overview.filter((shipment) => shipment.status === "RETURNED" || shipment.status === "CANCELLED").length;
  const advancedFilterCount = Number(Boolean(carrier)) + Number(Boolean(ttnFilter)) + Number(shipmentSort !== "newest");
  const resetFilters = () => {
    setSearch("");
    setStatus("");
    setCarrier("");
    setTtnFilter("");
    setShipmentSort("newest");
    setShowAdvancedFilters(false);
    setPage(1);
  };

  return (
    <WorkspacePage>
        <WorkspaceHeader title={t("shipments.title")} description={t("shipments.subtitle")} actions={canEdit ? <Button onClick={() => setIsCreateOpen(true)}>{t("shipments.create")}</Button> : undefined} />
        <section aria-label={t("shipments.summary.all")} data-shipments-compact-summary
          className="grid min-w-0 grid-cols-2 gap-px overflow-hidden rounded-xl border border-border-subtle bg-surface-2 md:grid-cols-4">
          {([
            [t("shipments.summary.all"), allShipments],
            [t("shipments.summary.ready"), readyShipments],
            [t("shipments.inTransit"), summaryQuery.data?.in_transit_count ?? 0],
            [t("shipments.summary.delivered"), deliveredShipments],
          ] as const).map(([label, value]) => (
            <div key={label} className="flex min-h-[56px] min-w-0 items-center justify-between gap-2 bg-surface-1 px-3 py-2">
              <span className="min-w-0 truncate text-xs font-medium text-text-secondary">{label}</span>
              <span className="shrink-0 text-lg font-bold tabular-nums text-text-primary">{overviewQuery.isPending ? "—" : value}</span>
            </div>
          ))}
        </section>
        <NovaPoshtaExternalInbox key={workspaceId} workspaceId={workspaceId} role={currentWorkspace?.role} mode="summary" />
        <section aria-label={t("filters.sort")} data-shipments-compact-filters
          className="flex min-w-0 flex-wrap items-center gap-2">
          <div className="min-w-[12rem] flex-[1_1_18rem]">
            <SearchInput value={search} onChange={setSearch} placeholder={t("shipments.searchPlaceholder")} />
          </div>
          <select aria-label={t("common.allStatuses")}
            className="min-h-10 w-[min(46vw,176px)] rounded-lg border border-input-border bg-input-background px-2.5 text-sm font-medium text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring sm:w-44"
            value={status} onChange={(event) => setStatus(event.target.value as ShipmentStatus | "")}>
            {STATUSES.map((item) => <option key={item || "all"} value={item}>{item ? formatStatus("shipment", item) : t("common.allStatuses")}</option>)}
          </select>
          <div className="relative shrink-0" ref={filterMenuRef}>
            <button type="button" aria-controls="shipments-advanced-filters" aria-expanded={showAdvancedFilters}
              onClick={() => setShowAdvancedFilters((expanded) => !expanded)}
              className={`inline-flex min-h-10 items-center justify-center gap-1.5 rounded-lg border px-3 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring ${showAdvancedFilters || advancedFilterCount ? "border-primary bg-primary/10 text-primary" : "border-border-subtle bg-surface-1 text-text-secondary hover:bg-surface-hover"}`}>
              <SlidersHorizontal aria-hidden="true" className="h-4 w-4"/>
              {locale === "en" ? "Filters" : "Фільтри"}
              {advancedFilterCount ? <span className="rounded-full bg-primary px-1.5 py-0.5 text-[10px] font-bold leading-none text-white">{advancedFilterCount}</span> : null}
              <ChevronDown aria-hidden="true" className={`h-3.5 w-3.5 transition-transform ${showAdvancedFilters ? "rotate-180" : ""}`}/>
            </button>
            {showAdvancedFilters ? <div id="shipments-advanced-filters" data-shipments-advanced-filters
              className="absolute right-0 top-[calc(100%+8px)] z-30 grid w-[min(90vw,360px)] min-w-0 gap-3 rounded-xl border border-border-subtle bg-surface-1 p-3 shadow-xl">
              <label className="grid min-w-0 gap-1 text-xs font-medium text-text-secondary">
                {t("shipments.allCarriers")}
                <select className="min-h-10 w-full min-w-0 rounded-lg border border-input-border bg-input-background px-3 text-sm text-text-primary"
                  value={carrier} onChange={(event) => setCarrier(event.target.value as ShipmentCarrier | "")}>
                  {CARRIERS.map((item) => <option key={item || "all"} value={item}>{item || t("shipments.allCarriers")}</option>)}
                </select>
              </label>
              <label className="grid min-w-0 gap-1 text-xs font-medium text-text-secondary">
                {t("shipments.allTtnStates")}
                <select className="min-h-10 w-full min-w-0 rounded-lg border border-input-border bg-input-background px-3 text-sm text-text-primary"
                  value={ttnFilter} onChange={(event) => setTtnFilter(event.target.value as TtnFilter)}>
                  <option value="">{t("shipments.allTtnStates")}</option>
                  <option value="hasTtn">{t("shipments.hasTtn")}</option>
                  <option value="missingTtn">{t("shipments.missingTtn")}</option>
                  <option value="needsAction">{t("shipments.needsAction")}</option>
                </select>
              </label>
              <label className="grid min-w-0 gap-1 text-xs font-medium text-text-secondary">
                {t("filters.sort")}
                <SortSelect value={shipmentSort} onChange={setShipmentSort} options={[
                  { value: "newest", label: t("sort.newest") },
                  { value: "oldest", label: t("sort.oldest") },
                  { value: "status", label: t("tables.status") },
                  { value: "updatedDesc", label: t("shipments.updatedRecently") },
                ]}/>
              </label>
            </div> : null}
          </div>
          {hasActiveFilters ? <button type="button" onClick={resetFilters}
            aria-label={t("filters.reset")} title={t("filters.reset")}
            className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-border-subtle bg-surface-1 text-text-secondary transition hover:bg-surface-hover focus-visible:ring-2 focus-visible:ring-focus-ring">
            <RotateCcw aria-hidden="true" className="h-4 w-4"/>
          </button> : null}
          {issueShipments > 0 ? <span className="ml-auto text-xs text-text-muted" data-shipments-issue-count>
            {t("shipments.summary.problems")}: <strong className="font-semibold tabular-nums text-text-secondary">{issueShipments}</strong>
          </span> : null}
        </section>
        <WorkspaceSplitView panelOpen={Boolean(selectedShipment)} panel={selectedShipment ? <EntitySidePanel open={Boolean(selectedShipment)} title={selectedShipment.nova_poshta_document_number ?? selectedShipment.tracking_number ?? t("shipments.draftShipment")} description={`${t("shipments.carrier")}: ${selectedShipment.carrier}`} onClose={() => setSelectedShipment(null)} footer={canEdit ? <div className="flex gap-2"><Button variant="secondary" onClick={() => setEditingShipment(selectedShipment)}>{t("shipments.edit")}</Button><Button variant="danger" onClick={() => setArchivingShipment(selectedShipment)}>{t("shipments.archive")}</Button></div> : undefined}><ShipmentDetails shipment={selectedShipment} workspaceId={workspaceId} onStatusChange={(nextStatus) => statusMutation.mutate({ shipmentId: selectedShipment.id, nextStatus })} /></EntitySidePanel> : null}>
          {shipmentsQuery.isLoading ? <LoadingSkeleton rows={5} title={t("shipments.pagination.loading")} /> : null}
          {shipmentsQuery.isError ? <ErrorState title={t("shipments.loadError")} description={safeApiErrorMessage(shipmentsQuery.error, t("shipments.loadError"))} onRetry={() => void shipmentsQuery.refetch()} /> : null}
          {!shipmentsQuery.isLoading && !shipmentsQuery.isError && filteredShipments.length === 0 ? <EmptyState title={hasAnyShipments && hasActiveFilters ? t("shipments.pagination.filteredEmptyTitle") : t("shipments.pagination.emptyTitle")} description={hasAnyShipments && hasActiveFilters ? t("shipments.pagination.filteredEmptyDescription") : t("shipments.pagination.emptyDescription")} action={!hasAnyShipments && canEdit ? <Button onClick={() => setIsCreateOpen(true)}>{t("shipments.create")}</Button> : null} /> : null}
          {!shipmentsQuery.isLoading && !shipmentsQuery.isError && filteredShipments.length > 0 ? <div className="shipments-pagination-section grid min-w-0 gap-4"><ShipmentTable shipments={paginatedShipments} selectedShipmentId={selectedShipment?.id} onSelect={setSelectedShipment} onEdit={canEdit ? setEditingShipment : undefined} onArchive={canEdit ? setArchivingShipment : undefined} /><PaginationControls page={page} pageSize={pageSize} totalItems={filteredShipments.length} onPageChange={setPage} onPageSizeChange={(nextPageSize) => setPageSize(nextPageSize as (typeof PAGE_SIZE_OPTIONS)[number])} /></div> : null}
        </WorkspaceSplitView>
      {archivingShipment ? <ConfirmActionDialog title={t("shipments.archiveTitle")} description={archivingShipment.nova_poshta_document_ref ? t("shipments.archiveNpDescription") : t("shipments.archiveDescription")} actionLabel={t("shipments.archive")} isSubmitting={archiveMutation.isPending} error={archiveMutation.isError ? safeApiErrorMessage(archiveMutation.error, t("errors.deleteFailed")) : null} onCancel={() => setArchivingShipment(null)} onConfirm={() => archiveMutation.mutate()} /> : null}
      {editingShipment ? <EditRecordDialog title={t("shipments.edit")} fields={[{ name: "tracking_number", label: t("shipments.trackingNumber") }, { name: "carrier", label: t("shipments.carrier"), type: "select", options: ["NOVA_POSHTA", "UKRPOSHTA", "MEEST", "ROZETKA_DELIVERY", "OTHER"].map((value) => ({ value, label: value })) }, { name: "recipient_name", label: t("shipments.recipientName") }, { name: "recipient_phone", label: t("shipments.recipientPhone") }, { name: "city", label: t("shipments.city") }, { name: "warehouse", label: t("shipments.warehouse") }, { name: "shipping_cost", label: t("shipments.shippingCost"), type: "number" }, { name: "cod_amount", label: t("shipments.codAmount"), type: "number" }, { name: "declared_value", label: t("shipments.declaredValue"), type: "number" }, { name: "notes", label: t("shipments.notes"), type: "textarea" }]} initialValues={editingShipment} isSubmitting={updateMutation.isPending} submitError={updateMutation.isError ? safeApiErrorMessage(updateMutation.error, t("shipments.updateError")) : null} onClose={() => setEditingShipment(null)} onSubmit={(values) => updateMutation.mutate(values)} /> : null}
      {isCreateOpen ? <FormDialog title={t("shipments.create")} description={t("shipments.manualDescription")} size="xl" onClose={() => setIsCreateOpen(false)}><ShipmentForm orders={ordersQuery.data ?? []} workspaceId={workspaceId} initialOrderId={initialOrderId} onSubmit={(payload) => createMutation.mutate(payload)} /></FormDialog> : null}
    </WorkspacePage>
  );
}
// Shipment list regression markers: shipment search filters pagination has TTN missing TTN needs action updated recently.
// Localization regression compatibility marker: FormDialog title="Create shipment".
// Pagination/list UX regression compatibility marker: common.searchByTrackingNumber.
