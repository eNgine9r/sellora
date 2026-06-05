"use client";

import { FormEvent, useState } from "react";
import { useI18n } from "@/i18n/provider";
import { CitySearchSelect } from "@/features/integrations/components/city-search-select";
import { WarehouseSearchSelect } from "@/features/integrations/components/warehouse-search-select";
import { buildShipmentCreatePayload } from "@/lib/payload-builders";
import { Order } from "@/types/orders";
import { ShipmentCarrier, ShipmentCreatePayload, ShipmentStatus } from "@/types/shipments";

const CARRIERS: ShipmentCarrier[] = ["NOVA_POSHTA", "UKRPOSHTA", "MEEST", "ROZETKA_DELIVERY", "OTHER"];
const STATUSES: ShipmentStatus[] = ["DRAFT", "CREATED", "IN_TRANSIT", "ARRIVED", "DELIVERED", "RETURNED", "CANCELLED"];

export function ShipmentForm({ orders, workspaceId, initialOrderId, onSubmit }: { orders: Order[]; workspaceId: string; initialOrderId?: string; onSubmit: (payload: ShipmentCreatePayload) => void }) {
  const { t, formatStatus } = useI18n();
  const [orderId, setOrderId] = useState(initialOrderId ?? "");
  const [trackingNumber, setTrackingNumber] = useState("");
  const [carrier, setCarrier] = useState<ShipmentCarrier>("NOVA_POSHTA");
  const [status, setStatus] = useState<ShipmentStatus>("DRAFT");
  const [recipientName, setRecipientName] = useState("");
  const [recipientPhone, setRecipientPhone] = useState("");
  const [city, setCity] = useState("");
  const [warehouse, setWarehouse] = useState("");
  const [novaPoshtaCityRef, setNovaPoshtaCityRef] = useState("");
  const [novaPoshtaWarehouseRef, setNovaPoshtaWarehouseRef] = useState("");
  const [shippingCost, setShippingCost] = useState("");
  const [codAmount, setCodAmount] = useState("");
  const [declaredValue, setDeclaredValue] = useState("");
  const [notes, setNotes] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = buildShipmentCreatePayload({ order_id: orderId, tracking_number: trackingNumber, carrier, status, recipient_name: recipientName, recipient_phone: recipientPhone, city, warehouse, nova_poshta_city_ref: novaPoshtaCityRef, nova_poshta_warehouse_ref: novaPoshtaWarehouseRef, shipping_cost: shippingCost, cod_amount: codAmount, declared_value: declaredValue, notes });
    if (!payload.order_id) {
      setValidationError(t("shipments.orderRequired"));
      return;
    }
    if (payload.status !== "DRAFT" && !payload.tracking_number) {
      setValidationError(t("shipments.trackingRequired"));
      return;
    }
    setValidationError(null);
    onSubmit(payload);
  }

  return (
    <form className="grid gap-4" onSubmit={submit}>
      <label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">{t("shipments.order")}<select className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" value={orderId} onChange={(event) => setOrderId(event.target.value)} required><option value="">{t("shipments.selectOrder")}</option>{orders.map((order) => <option key={order.id} value={order.id}>{order.order_number} · {order.status}</option>)}</select></label>
      <div className="grid gap-4 sm:grid-cols-2"><label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">{t("shipments.trackingTtn")}<input className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" value={trackingNumber} onChange={(event) => setTrackingNumber(event.target.value)} /></label><label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">{t("shipments.carrier")}<select className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" value={carrier} onChange={(event) => setCarrier(event.target.value as ShipmentCarrier)}>{CARRIERS.map((item) => <option key={item} value={item}>{item}</option>)}</select></label></div>
      <label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">{t("tables.status")}<select className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" value={status} onChange={(event) => setStatus(event.target.value as ShipmentStatus)}>{STATUSES.map((item) => <option key={item} value={item}>{formatStatus("shipment", item)}</option>)}</select></label>
      <div className="grid gap-4 sm:grid-cols-2"><label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">{t("shipments.recipient")}<input className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" value={recipientName} onChange={(event) => setRecipientName(event.target.value)} /></label><label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">{t("shipments.phone")}<input className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" value={recipientPhone} onChange={(event) => setRecipientPhone(event.target.value)} /></label></div>
      <div className="grid gap-4 sm:grid-cols-2"><label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">{t("shipments.city")}<input className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" value={city} onChange={(event) => setCity(event.target.value)} /></label><label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">{t("shipments.warehouse")}<input className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" value={warehouse} onChange={(event) => setWarehouse(event.target.value)} /></label></div>{carrier === "NOVA_POSHTA" ? <div className="grid gap-4 rounded-xl bg-slate-50 p-3 dark:bg-white/[0.04] sm:grid-cols-2"><CitySearchSelect workspaceId={workspaceId} query={city} onQuery={setCity} onSelect={(item) => { setCity(item.description); setNovaPoshtaCityRef(item.ref); setWarehouse(""); setNovaPoshtaWarehouseRef(""); }} /><WarehouseSearchSelect workspaceId={workspaceId} cityRef={novaPoshtaCityRef} query={warehouse} onQuery={setWarehouse} onSelect={(item) => { setWarehouse(item.description); setNovaPoshtaWarehouseRef(item.ref); }} /></div> : null}
      <div className="grid gap-4 sm:grid-cols-3"><label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">{t("shipments.shippingCost")}<input className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" inputMode="decimal" value={shippingCost} onChange={(event) => setShippingCost(event.target.value)} /></label><label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">{t("shipments.codAmount")}<input className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" inputMode="decimal" value={codAmount} onChange={(event) => setCodAmount(event.target.value)} /></label><label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">{t("shipments.declaredValue")}<input className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" inputMode="decimal" value={declaredValue} onChange={(event) => setDeclaredValue(event.target.value)} /></label></div>
      <label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">{t("shipments.notes")}<textarea className="min-h-24 rounded-lg border border-slate-300 px-3 py-2" value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
      {validationError ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">{validationError}</p> : null}
      <button className="min-h-11 rounded-xl bg-blue-600 px-4 py-3 font-bold text-white" type="submit">{t("shipments.create")}</button>
    </form>
  );
}
