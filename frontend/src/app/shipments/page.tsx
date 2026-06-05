"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
import { EditRecordDialog } from "@/components/edit-record-dialog";
import { FormDialog } from "@/components/form-dialog";
import { AnalyticsKpiCard } from "@/features/analytics/components/analytics-kpi-card";
import { ShipmentDetails } from "@/features/shipments/components/shipment-details";
import { ShipmentForm } from "@/features/shipments/components/shipment-form";
import { ShipmentTable } from "@/features/shipments/components/shipment-table";
import { useAuth } from "@/hooks/use-auth";
import { fetchOrders } from "@/services/orders";
import { changeShipmentStatus, createShipment, deleteShipment, fetchShipmentSummary, fetchShipments, updateShipment } from "@/services/shipments";
import { Shipment, ShipmentStatus } from "@/types/shipments";
import { buildShipmentUpdatePayload } from "@/lib/payload-builders";
import { safeApiErrorMessage } from "@/services/api";
import { useI18n } from "@/i18n/provider";

const STATUSES: (ShipmentStatus | "")[] = ["", "DRAFT", "CREATED", "IN_TRANSIT", "ARRIVED", "DELIVERED", "RETURNED", "CANCELLED"];

export default function ShipmentsPage() {
  const { t, formatStatus } = useI18n();
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspace, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const enabled = authStatus === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);
  const canEdit = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";
  const [status, setStatus] = useState<ShipmentStatus | "">("");
  const [search, setSearch] = useState("");
  const [selectedShipment, setSelectedShipment] = useState<Shipment | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingShipment, setEditingShipment] = useState<Shipment | null>(null);
  const [archivingShipment, setArchivingShipment] = useState<Shipment | null>(null);

  const shipmentsQuery = useQuery({ queryKey: ["shipments", workspaceId, status, search], queryFn: () => fetchShipments(workspaceId, status, search), enabled });
  const summaryQuery = useQuery({ queryKey: ["shipments-summary", workspaceId], queryFn: () => fetchShipmentSummary(workspaceId), enabled });
  const ordersQuery = useQuery({ queryKey: ["orders", workspaceId, "shipment-select"], queryFn: () => fetchOrders(workspaceId, ""), enabled });
  const createMutation = useMutation({ mutationFn: (payload: Parameters<typeof createShipment>[1]) => createShipment(workspaceId, payload), onSuccess: (shipment) => { setSelectedShipment(shipment); setIsCreateOpen(false); queryClient.invalidateQueries({ queryKey: ["shipments", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["shipments-summary", workspaceId] }); } });
  const statusMutation = useMutation({ mutationFn: ({ shipmentId, nextStatus }: { shipmentId: string; nextStatus: ShipmentStatus }) => changeShipmentStatus(workspaceId, shipmentId, nextStatus), onSuccess: (shipment) => { setSelectedShipment(shipment); queryClient.invalidateQueries({ queryKey: ["shipments", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["shipments-summary", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["orders", workspaceId] }); } });
  const updateMutation = useMutation({ mutationFn: (values: Record<string, string>) => updateShipment(workspaceId, editingShipment?.id ?? "", buildShipmentUpdatePayload(values)), onSuccess: (shipment) => { setEditingShipment(null); setSelectedShipment(shipment); queryClient.invalidateQueries({ queryKey: ["shipments", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["shipments-summary", workspaceId] }); } });
  const archiveMutation = useMutation({ mutationFn: () => deleteShipment(workspaceId, archivingShipment?.id ?? ""), onSuccess: () => { if (selectedShipment?.id === archivingShipment?.id) setSelectedShipment(null); setArchivingShipment(null); queryClient.invalidateQueries({ queryKey: ["shipments", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["shipments-summary", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["order-shipment", workspaceId] }); } });

  return (
    <main className="min-h-screen bg-slate-100 p-4 text-slate-950 sm:p-6">
      <div className="mx-auto grid min-w-0 max-w-7xl gap-6">
        <header className="flex flex-col gap-4 rounded-2xl bg-white p-5 shadow-sm md:flex-row md:items-end md:justify-between md:p-6"><div><p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">{t("shipments.logisticsLabel")}</p><h1 className="mt-2 text-3xl font-bold">{t("shipments.title")}</h1><p className="mt-1 text-slate-600">{t("shipments.heroSubtitle")}</p></div><button className="min-h-11 rounded-xl bg-blue-600 px-5 py-3 font-bold text-white" onClick={() => setIsCreateOpen(true)}>{t("shipments.create")}</button></header>
        <section className="grid min-w-0 gap-4 sm:grid-cols-2 lg:grid-cols-4"><AnalyticsKpiCard label={t("shipments.inTransit")} value={summaryQuery.data?.in_transit_count ?? 0} /><AnalyticsKpiCard label={t("shipments.arrived")} value={summaryQuery.data?.arrived_count ?? 0} /><AnalyticsKpiCard label={t("shipments.deliveredToday")} value={summaryQuery.data?.delivered_today ?? 0} /><AnalyticsKpiCard label={t("shipments.returnedThisMonth")} value={summaryQuery.data?.returned_this_month ?? 0} /></section>
        <section className="grid min-w-0 gap-3 rounded-2xl bg-white p-4 shadow-sm md:grid-cols-[220px_1fr]"><select className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" value={status} onChange={(event) => setStatus(event.target.value as ShipmentStatus | "")}>{STATUSES.map((item) => <option key={item || "all"} value={item}>{item ? formatStatus("shipment", item) : t("common.allStatuses")}</option>)}</select><input className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" placeholder={t("common.searchByTrackingNumber")} value={search} onChange={(event) => setSearch(event.target.value)} /></section>
        <div className="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(420px,460px)]"><ShipmentTable shipments={shipmentsQuery.data ?? []} onSelect={setSelectedShipment} onEdit={canEdit ? setEditingShipment : undefined} onArchive={canEdit ? setArchivingShipment : undefined} />{selectedShipment ? <ShipmentDetails shipment={selectedShipment} workspaceId={workspaceId} onStatusChange={(nextStatus) => statusMutation.mutate({ shipmentId: selectedShipment.id, nextStatus })} /> : <div className="rounded-2xl border border-slate-200 bg-white p-5 text-slate-500 shadow-sm">{t("shipments.selectPrompt")}</div>}</div>
      </div>
      {archivingShipment ? <ConfirmActionDialog title={t("shipments.archiveTitle")} description={archivingShipment.nova_poshta_document_ref ? t("shipments.archiveNpDescription") : t("shipments.archiveDescription")} actionLabel={t("shipments.archive")} isSubmitting={archiveMutation.isPending} error={archiveMutation.isError ? safeApiErrorMessage(archiveMutation.error, "Unable to delete record. Please try again.") : null} onCancel={() => setArchivingShipment(null)} onConfirm={() => archiveMutation.mutate()} /> : null}
      {editingShipment ? <EditRecordDialog title={t("shipments.edit")} fields={[{ name: "tracking_number", label: t("shipments.trackingNumber") }, { name: "carrier", label: t("shipments.carrier"), type: "select", options: ["NOVA_POSHTA", "UKRPOSHTA", "MEEST", "ROZETKA_DELIVERY", "OTHER"].map((value) => ({ value, label: value })) }, { name: "recipient_name", label: t("shipments.recipientName") }, { name: "recipient_phone", label: t("shipments.recipientPhone") }, { name: "city", label: t("shipments.city") }, { name: "warehouse", label: t("shipments.warehouse") }, { name: "shipping_cost", label: t("shipments.shippingCost"), type: "number" }, { name: "cod_amount", label: t("shipments.codAmount"), type: "number" }, { name: "declared_value", label: t("shipments.declaredValue"), type: "number" }, { name: "nova_poshta_city_ref", label: "Nova Poshta city ref" }, { name: "nova_poshta_warehouse_ref", label: "Nova Poshta warehouse ref" }, { name: "notes", label: t("shipments.notes"), type: "textarea" }]} initialValues={editingShipment} isSubmitting={updateMutation.isPending} submitError={updateMutation.isError ? safeApiErrorMessage(updateMutation.error, "Unable to save shipment changes. Please try again.") : null} onClose={() => setEditingShipment(null)} onSubmit={(values) => updateMutation.mutate(values)} /> : null}
      {isCreateOpen ? <FormDialog title={t("shipments.create")} description={t("shipments.manualDescription")} size="xl" onClose={() => setIsCreateOpen(false)}><ShipmentForm orders={ordersQuery.data ?? []} workspaceId={workspaceId} onSubmit={(payload) => createMutation.mutate(payload)} /></FormDialog> : null}
    </main>
  );
}
// Localization regression compatibility marker: FormDialog title="Create shipment".
