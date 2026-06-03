"use client";

import { FormEvent, useState } from "react";
import { Order } from "@/types/orders";
import { ShipmentCarrier, ShipmentCreatePayload, ShipmentStatus } from "@/types/shipments";

const CARRIERS: ShipmentCarrier[] = ["NOVA_POSHTA", "UKRPOSHTA", "MEEST", "ROZETKA_DELIVERY", "OTHER"];
const STATUSES: ShipmentStatus[] = ["DRAFT", "CREATED", "IN_TRANSIT", "ARRIVED", "DELIVERED", "RETURNED", "CANCELLED"];

export function ShipmentForm({ orders, initialOrderId, onSubmit }: { orders: Order[]; initialOrderId?: string; onSubmit: (payload: ShipmentCreatePayload) => void }) {
  const [orderId, setOrderId] = useState(initialOrderId ?? "");
  const [trackingNumber, setTrackingNumber] = useState("");
  const [carrier, setCarrier] = useState<ShipmentCarrier>("NOVA_POSHTA");
  const [status, setStatus] = useState<ShipmentStatus>("DRAFT");
  const [recipientName, setRecipientName] = useState("");
  const [recipientPhone, setRecipientPhone] = useState("");
  const [city, setCity] = useState("");
  const [warehouse, setWarehouse] = useState("");
  const [shippingCost, setShippingCost] = useState("");
  const [codAmount, setCodAmount] = useState("");
  const [declaredValue, setDeclaredValue] = useState("");
  const [notes, setNotes] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({ order_id: orderId, tracking_number: trackingNumber || undefined, carrier, status, recipient_name: recipientName || undefined, recipient_phone: recipientPhone || undefined, city: city || undefined, warehouse: warehouse || undefined, shipping_cost: shippingCost || undefined, cod_amount: codAmount || undefined, declared_value: declaredValue || undefined, notes: notes || undefined });
  }

  return (
    <form className="grid gap-4" onSubmit={submit}>
      <label className="grid gap-2 text-sm font-semibold text-slate-700">Order<select className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" value={orderId} onChange={(event) => setOrderId(event.target.value)} required><option value="">Select order</option>{orders.map((order) => <option key={order.id} value={order.id}>{order.order_number} · ${order.revenue} · {order.status}</option>)}</select></label>
      <div className="grid gap-4 sm:grid-cols-2"><label className="grid gap-2 text-sm font-semibold text-slate-700">Tracking / TTN<input className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" value={trackingNumber} onChange={(event) => setTrackingNumber(event.target.value)} /></label><label className="grid gap-2 text-sm font-semibold text-slate-700">Carrier<select className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" value={carrier} onChange={(event) => setCarrier(event.target.value as ShipmentCarrier)}>{CARRIERS.map((item) => <option key={item} value={item}>{item}</option>)}</select></label></div>
      <label className="grid gap-2 text-sm font-semibold text-slate-700">Status<select className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" value={status} onChange={(event) => setStatus(event.target.value as ShipmentStatus)}>{STATUSES.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
      <div className="grid gap-4 sm:grid-cols-2"><label className="grid gap-2 text-sm font-semibold text-slate-700">Recipient<input className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" value={recipientName} onChange={(event) => setRecipientName(event.target.value)} /></label><label className="grid gap-2 text-sm font-semibold text-slate-700">Phone<input className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" value={recipientPhone} onChange={(event) => setRecipientPhone(event.target.value)} /></label></div>
      <div className="grid gap-4 sm:grid-cols-2"><label className="grid gap-2 text-sm font-semibold text-slate-700">City<input className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" value={city} onChange={(event) => setCity(event.target.value)} /></label><label className="grid gap-2 text-sm font-semibold text-slate-700">Warehouse<input className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" value={warehouse} onChange={(event) => setWarehouse(event.target.value)} /></label></div>
      <div className="grid gap-4 sm:grid-cols-3"><label className="grid gap-2 text-sm font-semibold text-slate-700">Shipping cost<input className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" inputMode="decimal" value={shippingCost} onChange={(event) => setShippingCost(event.target.value)} /></label><label className="grid gap-2 text-sm font-semibold text-slate-700">COD amount<input className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" inputMode="decimal" value={codAmount} onChange={(event) => setCodAmount(event.target.value)} /></label><label className="grid gap-2 text-sm font-semibold text-slate-700">Declared value<input className="min-h-11 rounded-lg border border-slate-300 px-3 py-2" inputMode="decimal" value={declaredValue} onChange={(event) => setDeclaredValue(event.target.value)} /></label></div>
      <label className="grid gap-2 text-sm font-semibold text-slate-700">Notes<textarea className="min-h-24 rounded-lg border border-slate-300 px-3 py-2" value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
      <button className="min-h-11 rounded-xl bg-blue-600 px-4 py-3 font-bold text-white" type="submit">Create shipment</button>
    </form>
  );
}
