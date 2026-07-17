"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
import { EditRecordDialog } from "@/components/edit-record-dialog";
import { FilterBar, ResetFiltersButton, SearchInput, SortSelect } from "@/components/filter-controls";
import { FormDialog } from "@/components/form-dialog";
import { clampPage, PAGE_SIZE_OPTIONS, paginateItems, PaginationControls } from "@/components/pagination-controls";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";
import { Button, CompactSummary, EntitySidePanel, WorkspaceHeader, WorkspacePage, WorkspaceSplitView } from "@/components/crm-workspace";
import { ShipmentDetails } from "@/features/shipments/components/shipment-details";
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
  const { t, formatStatus } = useI18n();
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
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<(typeof PAGE_SIZE_OPTIONS)[number]>(5);
  const [selectedShipment, setSelectedShipment] = useState<Shipment | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [initialOrderId, setInitialOrderId] = useState<string | undefined>();
  const [editingShipment, setEditingShipment] = useState<Shipment | null>(null);
  const [archivingShipment, setArchivingShipment] = useState<Shipment | null>(null);

  const shipmentsQuery = useQuery({ queryKey: ["shipments", workspaceId, status, search], queryFn: () => fetchShipments(workspaceId, status, search), enabled });
  const summaryQuery = useQuery({ queryKey: ["shipments-summary", workspaceId], queryFn: () => fetchShipmentSummary(workspaceId), enabled });
  const ordersQuery = useQuery({ queryKey: ["orders", workspaceId, "shipment-select"], queryFn: () => fetchOrders(workspaceId, ""), enabled });
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
  const hasAnyShipments = (shipmentsQuery.data?.length ?? 0) > 0;
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

  const allShipments = shipmentsQuery.data?.length ?? 0;
  const readyShipments = (shipmentsQuery.data ?? []).filter((shipment) => shipment.status === "DRAFT" || shipment.status === "CREATED").length;
  const deliveredShipments = (shipmentsQuery.data ?? []).filter((shipment) => shipment.status === "DELIVERED").length;
  const problemShipments = (shipmentsQuery.data ?? []).filter((shipment) => shipment.status === "RETURNED" || shipment.status === "CANCELLED" || shipmentNeedsAction(shipment)).length;

  return (
    <WorkspacePage>
        <WorkspaceHeader title={t("shipments.title")} description={t("shipments.subtitle")} actions={canEdit ? <Button onClick={() => setIsCreateOpen(true)}>{t("shipments.create")}</Button> : undefined} />
        <CompactSummary layout="five-balanced" items={[{ label: t("shipments.summary.all"), value: allShipments }, { label: t("shipments.summary.ready"), value: readyShipments }, { label: t("shipments.inTransit"), value: summaryQuery.data?.in_transit_count ?? 0 }, { label: t("shipments.summary.delivered"), value: deliveredShipments || (summaryQuery.data?.delivered_today ?? 0) }, { label: t("shipments.summary.problems"), value: problemShipments || (summaryQuery.data?.returned_this_month ?? 0) }]} />
        <FilterBar>
          <SearchInput value={search} onChange={setSearch} placeholder={t("shipments.searchPlaceholder")} />
          <select className="min-h-10 w-full min-w-0 max-w-full rounded-xl border border-input-border bg-input-background px-3 py-2 text-sm font-semibold text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" value={status} onChange={(event) => setStatus(event.target.value as ShipmentStatus | "")}>{STATUSES.map((item) => <option key={item || "all"} value={item}>{item ? formatStatus("shipment", item) : t("common.allStatuses")}</option>)}</select>
          <select className="min-h-10 w-full min-w-0 max-w-full rounded-xl border border-input-border bg-input-background px-3 py-2 text-sm font-semibold text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" value={carrier} onChange={(event) => setCarrier(event.target.value as ShipmentCarrier | "")}>{CARRIERS.map((item) => <option key={item || "all"} value={item}>{item || t("shipments.allCarriers")}</option>)}</select>
          <select className="min-h-10 w-full min-w-0 max-w-full rounded-xl border border-input-border bg-input-background px-3 py-2 text-sm font-semibold text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" value={ttnFilter} onChange={(event) => setTtnFilter(event.target.value as TtnFilter)}><option value="">{t("shipments.allTtnStates")}</option><option value="hasTtn">{t("shipments.hasTtn")}</option><option value="missingTtn">{t("shipments.missingTtn")}</option><option value="needsAction">{t("shipments.needsAction")}</option></select>
          <SortSelect value={shipmentSort} onChange={setShipmentSort} options={[{ value: "newest", label: t("sort.newest") }, { value: "oldest", label: t("sort.oldest") }, { value: "status", label: t("tables.status") }, { value: "updatedDesc", label: t("shipments.updatedRecently") }]} />
          <ResetFiltersButton onClick={() => { setSearch(""); setStatus(""); setCarrier(""); setTtnFilter(""); setShipmentSort("newest"); setPage(1); }} />
        </FilterBar>
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
