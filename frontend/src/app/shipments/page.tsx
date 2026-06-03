"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { AnalyticsKpiCard } from "@/features/analytics/components/analytics-kpi-card";
import { ShipmentDetails } from "@/features/shipments/components/shipment-details";
import { ShipmentForm } from "@/features/shipments/components/shipment-form";
import { ShipmentTable } from "@/features/shipments/components/shipment-table";
import { useAuth } from "@/hooks/use-auth";
import { fetchOrders } from "@/services/orders";
import { changeShipmentStatus, createShipment, fetchShipmentSummary, fetchShipments } from "@/services/shipments";
import { Shipment, ShipmentStatus } from "@/types/shipments";

const STATUSES: (ShipmentStatus | "")[] = ["", "DRAFT", "CREATED", "IN_TRANSIT", "ARRIVED", "DELIVERED", "RETURNED", "CANCELLED"];

export default function ShipmentsPage() {
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const enabled = authStatus === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);
  const [status, setStatus] = useState<ShipmentStatus | "">("");
  const [search, setSearch] = useState("");
  const [selectedShipment, setSelectedShipment] = useState<Shipment | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const shipmentsQuery = useQuery({ queryKey: ["shipments", workspaceId, status, search], queryFn: () => fetchShipments(workspaceId, status, search), enabled });
  const summaryQuery = useQuery({ queryKey: ["shipments-summary", workspaceId], queryFn: () => fetchShipmentSummary(workspaceId), enabled });
  const ordersQuery = useQuery({ queryKey: ["orders", workspaceId, "shipment-select"], queryFn: () => fetchOrders(workspaceId, ""), enabled });
  const createMutation = useMutation({ mutationFn: (payload: Parameters<typeof createShipment>[1]) => createShipment(workspaceId, payload), onSuccess: (shipment) => { setSelectedShipment(shipment); setIsCreateOpen(false); queryClient.invalidateQueries({ queryKey: ["shipments", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["shipments-summary", workspaceId] }); } });
  const statusMutation = useMutation({ mutationFn: ({ shipmentId, nextStatus }: { shipmentId: string; nextStatus: ShipmentStatus }) => changeShipmentStatus(workspaceId, shipmentId, nextStatus), onSuccess: (shipment) => { setSelectedShipment(shipment); queryClient.invalidateQueries({ queryKey: ["shipments", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["shipments-summary", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["orders", workspaceId] }); } });

  return (
    <main className="min-h-screen bg-slate-100 p-4 text-slate-950 sm:p-6">
      <div className="mx-auto grid max-w-7xl gap-6">
        <header className="flex flex-col gap-4 rounded-2xl bg-white p-5 shadow-sm md:flex-row md:items-end md:justify-between md:p-6"><div><p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Sellora Logistics</p><h1 className="mt-2 text-3xl font-bold">Shipments</h1><p className="mt-1 text-slate-600">Create TTN records manually, track delivery lifecycle, and keep order statuses in sync.</p></div><button className="min-h-11 rounded-xl bg-blue-600 px-5 py-3 font-bold text-white" onClick={() => setIsCreateOpen(true)}>Create shipment</button></header>
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><AnalyticsKpiCard label="In Transit" value={summaryQuery.data?.in_transit_count ?? 0} /><AnalyticsKpiCard label="Arrived" value={summaryQuery.data?.arrived_count ?? 0} /><AnalyticsKpiCard label="Delivered Today" value={summaryQuery.data?.delivered_today ?? 0} /><AnalyticsKpiCard label="Returned This Month" value={summaryQuery.data?.returned_this_month ?? 0} /></section>
        <section className="grid gap-3 rounded-2xl bg-white p-4 shadow-sm md:grid-cols-[220px_1fr]"><select className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" value={status} onChange={(event) => setStatus(event.target.value as ShipmentStatus | "")}>{STATUSES.map((item) => <option key={item || "all"} value={item}>{item || "All statuses"}</option>)}</select><input className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" placeholder="Search by tracking number" value={search} onChange={(event) => setSearch(event.target.value)} /></section>
        <div className="grid gap-6 xl:grid-cols-[1fr_380px]"><ShipmentTable shipments={shipmentsQuery.data ?? []} onSelect={setSelectedShipment} />{selectedShipment ? <ShipmentDetails shipment={selectedShipment} onStatusChange={(nextStatus) => statusMutation.mutate({ shipmentId: selectedShipment.id, nextStatus })} /> : <div className="rounded-2xl border border-slate-200 bg-white p-5 text-slate-500 shadow-sm">Select a shipment to view details and status actions.</div>}</div>
      </div>
      {isCreateOpen ? <div className="fixed inset-0 z-40 overflow-y-auto bg-slate-950/50 p-0 sm:p-4"><div className="min-h-full bg-white p-5 shadow-xl sm:mx-auto sm:max-w-3xl sm:rounded-2xl sm:p-6"><div className="mb-4 flex items-center justify-between gap-3"><div><h2 className="text-xl font-bold">Create shipment</h2><p className="text-sm text-slate-500">Manual shipment entry only; Nova Poshta API is not connected.</p></div><button className="min-h-11 rounded-xl border border-slate-300 px-4 py-2 font-bold" onClick={() => setIsCreateOpen(false)}>Close</button></div><ShipmentForm orders={ordersQuery.data ?? []} onSubmit={(payload) => createMutation.mutate(payload)} /></div></div> : null}
    </main>
  );
}
