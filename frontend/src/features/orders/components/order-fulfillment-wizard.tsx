"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { CitySearchSelect } from "@/features/integrations/components/city-search-select";
import { WarehouseSearchSelect } from "@/features/integrations/components/warehouse-search-select";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import { fetchCustomerAddresses } from "@/services/crm-completion";
import { finalizeDirectCustomerOrder } from "@/services/direct";
import { fetchNovaPoshtaReadiness } from "@/services/integrations";
import { createOrderFulfillment } from "@/services/order-fulfillments";
import { safeApiErrorMessage } from "@/services/api";
import { AdCampaign } from "@/types/advertising";
import { Customer } from "@/types/crm";
import { OrderFulfillmentPayload, OrderFulfillmentResult } from "@/types/order-fulfillment";
import { Inventory, Product, ProductVariant } from "@/types/products";

type WizardItem = { key: string; product_variant_id: string; quantity: string; unit_price: string };
const newKey = () => globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
const emptyItem = (): WizardItem => ({ key: newKey(), product_variant_id: "", quantity: "1", unit_price: "" });
const inputClass = "min-h-11 w-full min-w-0 rounded-xl border border-input-border bg-input-background px-3 py-2 text-sm font-semibold text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring";

function normalizeUaPhonePreview(value: string) {
  const raw = value.trim();
  if (!raw || /[A-Za-zА-Яа-яІіЇїЄє]/.test(raw)) return null;
  const digits = raw.replace(/[^0-9]/g, "");
  if (digits.length === 10 && digits.startsWith("0")) return `+38${digits}`;
  if (digits.length === 12 && digits.startsWith("380")) return `+${digits}`;
  return null;
}

export function OrderFulfillmentWizard({
  workspaceId,
  customers,
  variants,
  products,
  inventory,
  campaigns,
  currencyCode,
  showProfit,
  initialCustomerId,
  sourceDirectConversationId,
  onSuccess,
}: {
  workspaceId: string;
  customers: Customer[];
  variants: ProductVariant[];
  products: Product[];
  inventory: Inventory[];
  campaigns: AdCampaign[];
  currencyCode: string;
  showProfit: boolean;
  initialCustomerId?: string | null;
  sourceDirectConversationId?: string | null;
  onSuccess: (result: OrderFulfillmentResult) => void;
}) {
  const { t, formatStatus } = useI18n();
  const submitLock = useRef(false);
  const initialCustomerApplied = useRef(false);
  const idempotencyKey = useRef(newKey());
  const [step, setStep] = useState(1);
  const [mode, setMode] = useState<"existing" | "new">("existing");
  const [customerSearch, setCustomerSearch] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const [instagram, setInstagram] = useState("");
  const [addressId, setAddressId] = useState("");
  const [recipientName, setRecipientName] = useState("");
  const [recipientPhone, setRecipientPhone] = useState("");
  const [city, setCity] = useState("");
  const [cityRef, setCityRef] = useState("");
  const [warehouse, setWarehouse] = useState("");
  const [warehouseRef, setWarehouseRef] = useState("");
  const [warehouseNumber, setWarehouseNumber] = useState("");
  const [saveAddress, setSaveAddress] = useState(true);
  const [items, setItems] = useState<WizardItem[]>([emptyItem()]);
  const [paymentStatus, setPaymentStatus] = useState<"PENDING" | "PAID" | "COD">("COD");
  const [codAmount, setCodAmount] = useState("");
  const [declaredValue, setDeclaredValue] = useState("");
  const [campaignId, setCampaignId] = useState("");
  const [shippingCost, setShippingCost] = useState("0");
  const [adCost, setAdCost] = useState("0");
  const [codFee, setCodFee] = useState("0");
  const [otherCost, setOtherCost] = useState("0");
  const [notes, setNotes] = useState("");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [automationWarning, setAutomationWarning] = useState<string | null>(null);
  const [result, setResult] = useState<OrderFulfillmentResult | null>(null);

  const selectedCustomer = customers.find((customer) => customer.id === customerId) ?? null;
  const addressesQuery = useQuery({
    queryKey: ["customer-addresses", workspaceId, customerId, "fulfillment"],
    queryFn: () => fetchCustomerAddresses(workspaceId, customerId),
    enabled: Boolean(customerId),
  });
  const readinessQuery = useQuery({
    queryKey: ["nova-poshta-readiness", workspaceId],
    queryFn: () => fetchNovaPoshtaReadiness(workspaceId),
    enabled: Boolean(workspaceId),
  });
  const mutation = useMutation({
    mutationFn: (payload: OrderFulfillmentPayload) => createOrderFulfillment(workspaceId, payload),
    onSuccess: async (nextResult) => {
      setAutomationWarning(null);
      if (sourceDirectConversationId) {
        try {
          await finalizeDirectCustomerOrder(sourceDirectConversationId, {
            order_id: nextResult.order.id,
            name: recipientName.trim(),
            phone: normalizeUaPhonePreview(recipientPhone) || recipientPhone,
            city: city.trim(),
            region: null,
            recipient_name: recipientName.trim(),
            recipient_phone: normalizeUaPhonePreview(recipientPhone) || recipientPhone,
            warehouse: warehouse.trim(),
            warehouse_number: warehouseNumber || null,
            nova_poshta_city_ref: cityRef,
            nova_poshta_warehouse_ref: warehouseRef,
          });
        } catch {
          setAutomationWarning("Замовлення створено, але зв’язок із Direct потребує повторної синхронізації.");
        }
      }
      setResult(nextResult);
      onSuccess(nextResult);
    },
    onError: (requestError) => {
      submitLock.current = false;
      setError(safeApiErrorMessage(requestError, t("fulfillment.submitError")));
    },
  });

  useEffect(() => {
    idempotencyKey.current = newKey();
    submitLock.current = false;
    initialCustomerApplied.current = false;
    setResult(null);
    setAutomationWarning(null);
  }, [workspaceId]);

  useEffect(() => {
    if (!initialCustomerId || initialCustomerApplied.current) return;
    const customer = customers.find((row) => row.id === initialCustomerId);
    if (!customer) return;
    initialCustomerApplied.current = true;
    setMode("existing");
    setCustomerId(customer.id);
    setCustomerSearch(customer.name);
    setRecipientName(customer.name);
    setRecipientPhone(customer.phone || "");
    setAddressId("");
  }, [customers, initialCustomerId]);

  useEffect(() => {
    const defaultAddress = addressesQuery.data?.find((address) => address.is_default) ?? addressesQuery.data?.[0];
    if (!defaultAddress) return;
    setAddressId(defaultAddress.id);
    setRecipientName(defaultAddress.recipient_name || selectedCustomer?.name || "");
    setRecipientPhone(defaultAddress.phone || selectedCustomer?.phone || "");
    setCity(defaultAddress.city || "");
    setCityRef(defaultAddress.nova_poshta_city_ref || "");
    setWarehouse(defaultAddress.address_line1 || "");
    setWarehouseRef(defaultAddress.nova_poshta_warehouse_ref || "");
    setWarehouseNumber(defaultAddress.warehouse_number || "");
  }, [addressesQuery.data, selectedCustomer?.id, selectedCustomer?.name, selectedCustomer?.phone]);

  const productById = useMemo(() => new Map(products.map((product) => [product.id, product])), [products]);
  const inventoryByVariant = useMemo(() => new Map(inventory.map((stock) => [stock.product_variant_id, stock])), [inventory]);
  const filteredCustomers = useMemo(() => {
    const query = customerSearch.trim().toLocaleLowerCase();
    return customers.filter((customer) => !query || [customer.name, customer.phone, customer.instagram_username].some((value) => value?.toLocaleLowerCase().includes(query))).slice(0, 8);
  }, [customerSearch, customers]);
  const total = items.reduce((sum, item) => sum + Number(item.quantity || 0) * Number(item.unit_price || 0), 0);
  const normalizedPhone = normalizeUaPhonePreview(recipientPhone);
  const normalizedCustomerPhone = normalizeUaPhonePreview(customerPhone);
  const costs = Number(shippingCost || 0) + Number(adCost || 0) + Number(codFee || 0) + Number(otherCost || 0);
  const canCreateTtn = readinessQuery.data?.provider_writes_enabled === true;
  const writeBlockers = readinessQuery.data?.write_blockers ?? [];

  useEffect(() => {
    if (paymentStatus === "COD") setCodAmount(String(total || ""));
    else setCodAmount("0");
    setDeclaredValue((current) => !current || Number(current) === 0 ? String(total || "") : current);
  }, [paymentStatus, total]);

  function selectCustomer(customer: Customer) {
    setCustomerId(customer.id);
    setCustomerSearch(customer.name);
    setRecipientName(customer.name);
    setRecipientPhone(customer.phone || "");
    setAddressId("");
    setCity("");
    setCityRef("");
    setWarehouse("");
    setWarehouseRef("");
  }

  function updateItem(key: string, patch: Partial<WizardItem>) {
    setItems((current) => current.map((item) => item.key === key ? { ...item, ...patch } : item));
  }

  function selectVariant(item: WizardItem, variantId: string) {
    const variant = variants.find((row) => row.id === variantId);
    updateItem(item.key, { product_variant_id: variantId, unit_price: variant?.price || "0" });
  }

  function validateStep(nextStep: number) {
    if (nextStep > 1) {
      if (mode === "existing" && !customerId) return t("fulfillment.validation.customer");
      if (mode === "new" && !customerName.trim()) return t("fulfillment.validation.name");
      if (mode === "new" && customerPhone.trim() && !normalizedCustomerPhone) return t("fulfillment.validation.phone");
      if (!recipientName.trim()) return t("fulfillment.validation.recipient");
      if (!normalizedPhone) return t("fulfillment.validation.phone");
      if (!cityRef || !city.trim()) return t("fulfillment.validation.city");
      if (!warehouseRef || !warehouse.trim()) return t("fulfillment.validation.warehouse");
    }
    if (nextStep > 2) {
      if (!items.length || items.some((item) => !item.product_variant_id || Number(item.quantity) < 1 || Number(item.unit_price) < 0)) return t("fulfillment.validation.items");
      for (const item of items) {
        const stock = inventoryByVariant.get(item.product_variant_id);
        if (stock && stock.stock_quantity - stock.reserved_quantity < Number(item.quantity)) return t("fulfillment.validation.stock");
      }
    }
    return null;
  }

  function goTo(nextStep: number) {
    const validation = validateStep(nextStep);
    if (validation) {
      setError(validation);
      return;
    }
    setError(null);
    setStep(nextStep);
  }

  function submit(createTtn: boolean) {
    if (submitLock.current || mutation.isPending) return;
    const validation = validateStep(3);
    if (validation) {
      setError(validation);
      return;
    }
    submitLock.current = true;
    setError(null);
    mutation.mutate({
      idempotency_key: idempotencyKey.current,
      customer_id: mode === "existing" ? customerId : null,
      customer_name: mode === "new" ? customerName.trim() : null,
      customer_phone: mode === "new" ? (normalizedCustomerPhone || normalizedPhone) : null,
      instagram_username: mode === "new" ? instagram.trim() || null : null,
      address_id: addressId || null,
      recipient_name: recipientName.trim(),
      recipient_phone: normalizedPhone || recipientPhone,
      nova_poshta_city_ref: cityRef,
      city: city.trim(),
      nova_poshta_warehouse_ref: warehouseRef,
      warehouse: warehouse.trim(),
      warehouse_number: warehouseNumber || null,
      save_address_as_default: saveAddress,
      items: items.map((item) => ({ product_variant_id: item.product_variant_id, quantity: Number(item.quantity), unit_price: Number(item.unit_price), unit_cost: 0 })),
      payment_status: paymentStatus,
      cod_amount: paymentStatus === "COD" ? Number(codAmount || total) : 0,
      declared_value: Number(declaredValue || total),
      campaign_id: campaignId || null,
      ad_cost: Number(adCost || 0),
      shipping_cost: Number(shippingCost || 0),
      cod_fee: Number(codFee || 0),
      other_cost: Number(otherCost || 0),
      notes: notes.trim() || null,
      create_ttn: createTtn,
    });
  }

  if (result) {
    const success = result.result_code === "ORDER_AND_TTN_CREATED";
    const reconciliation = result.result_code === "ORDER_CREATED_PROVIDER_RECONCILIATION_REQUIRED";
    return (
      <div className="grid gap-5 text-center">
        <div className={`rounded-2xl border p-5 ${success ? "border-emerald-300 bg-emerald-50 dark:border-emerald-400/30 dark:bg-emerald-500/15" : reconciliation ? "border-amber-300 bg-amber-50 dark:border-amber-400/30 dark:bg-amber-500/15" : "border-blue-300 bg-blue-50 dark:border-blue-400/30 dark:bg-blue-500/15"}`}>
          <h3 className="text-xl font-black text-text-primary">{t(`fulfillment.result.${result.result_code}`)}</h3>
          <p className="mt-2 text-sm text-text-secondary">{result.order.order_number}</p>
          {sourceDirectConversationId && !automationWarning ? <p className="mt-2 text-sm font-bold text-emerald-700">Діалог, клієнт і замовлення автоматично пов’язані.</p> : null}
          {automationWarning ? <p className="mt-2 text-sm font-bold text-amber-700">{automationWarning}</p> : null}
          {result.tracking_number ? <p className="mt-3 text-2xl font-black text-text-primary">{result.tracking_number}</p> : null}
          {result.provider_error_code ? <p className="mt-3 text-sm font-semibold text-text-secondary">{t("fulfillment.providerActionRequired")}</p> : null}
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          {result.retry_available && canCreateTtn ? <button className={inputClass} type="button" onClick={() => { submitLock.current = false; setResult(null); submit(true); }}>{t("fulfillment.retryTtn")}</button> : null}
          {result.tracking_number ? <button className={inputClass} type="button" onClick={() => void navigator.clipboard.writeText(result.tracking_number || "")}>{t("fulfillment.copyTtn")}</button> : null}
          {sourceDirectConversationId ? <Link className={`${inputClass} flex items-center justify-center`} href={`/direct?conversation=${encodeURIComponent(sourceDirectConversationId)}`}>Повернутися в Direct</Link> : null}
          <Link className={`${inputClass} flex items-center justify-center`} href={`/orders?order_id=${result.order.id}`}>{t("fulfillment.openOrder")}</Link>
          <Link className={`${inputClass} flex items-center justify-center`} href={`/shipments?order_id=${result.order.id}`}>{t("fulfillment.openShipment")}</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="grid min-w-0 gap-4" data-direct-order-wizard={sourceDirectConversationId ? "true" : undefined}>
      {sourceDirectConversationId ? <div className="rounded-xl border border-violet-300 bg-violet-50 p-3 text-sm font-semibold text-violet-900 dark:border-violet-400/30 dark:bg-violet-500/15 dark:text-violet-100">Замовлення створюється з Instagram Direct. Клієнт уже вибраний; введені контактні дані та адреса автоматично доповнять його картку.</div> : null}
      <ol className="grid grid-cols-3 gap-2" aria-label={t("fulfillment.progress")}>
        {[1, 2, 3].map((number) => <li className={`rounded-xl px-2 py-2 text-center text-xs font-bold ${step === number ? "bg-primary text-primary-foreground" : step > number ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-100" : "bg-surface-2 text-text-secondary"}`} key={number}>{number}. {t(`fulfillment.step${number}`)}</li>)}
      </ol>

      <div className="sellora-scrollbar grid max-h-[calc(100dvh-16rem)] min-w-0 gap-4 overflow-y-auto overflow-x-hidden pr-1">
        {step === 1 ? <>
          <div className="grid grid-cols-2 gap-2 rounded-xl bg-surface-2 p-1">
            <button className={`min-h-11 rounded-lg font-bold ${mode === "existing" ? "bg-surface-1 shadow-sm" : "text-text-secondary"}`} type="button" onClick={() => setMode("existing")}>{t("fulfillment.existingCustomer")}</button>
            <button className={`min-h-11 rounded-lg font-bold ${mode === "new" ? "bg-surface-1 shadow-sm" : "text-text-secondary"}`} type="button" disabled={Boolean(sourceDirectConversationId)} onClick={() => { setMode("new"); setCustomerId(""); }}>{t("fulfillment.newCustomer")}</button>
          </div>
          {mode === "existing" ? <section className="grid gap-3 rounded-2xl border border-border-subtle p-3">
            <input className={inputClass} placeholder={t("orders.customerSearchPlaceholder")} value={customerSearch} onChange={(event) => setCustomerSearch(event.target.value)} />
            <div className="grid max-h-44 gap-1 overflow-y-auto">
              {filteredCustomers.map((customer) => <button className={`rounded-xl px-3 py-2 text-left ${customer.id === customerId ? "bg-surface-selected ring-1 ring-primary" : "hover:bg-surface-hover"}`} key={customer.id} type="button" onClick={() => selectCustomer(customer)}><strong className="block">{customer.name}</strong><span className="text-xs text-text-secondary">{[customer.phone, customer.instagram_username ? `@${customer.instagram_username.replace(/^@/, "")}` : null].filter(Boolean).join(" · ")}</span></button>)}
            </div>
          </section> : <section className="grid gap-3 rounded-2xl border border-border-subtle p-3 sm:grid-cols-2">
            <label className="grid gap-1 text-sm font-semibold">{t("customers.name")}<input className={inputClass} value={customerName} onChange={(event) => { setCustomerName(event.target.value); setRecipientName(event.target.value); }} /></label>
            <label className="grid gap-1 text-sm font-semibold">{t("customers.phone")}<input className={inputClass} inputMode="tel" value={customerPhone} onChange={(event) => { setCustomerPhone(event.target.value); setRecipientPhone(event.target.value); }} /></label>
            <label className="grid gap-1 text-sm font-semibold sm:col-span-2">Instagram<input className={inputClass} value={instagram} onChange={(event) => setInstagram(event.target.value)} /></label>
          </section>}
          <section className="grid gap-3 rounded-2xl border border-border-subtle p-3 sm:grid-cols-2">
            <h3 className="font-black sm:col-span-2">{t("fulfillment.recipientAndDelivery")}</h3>
            <label className="grid gap-1 text-sm font-semibold">{t("fulfillment.recipientName")}<input className={inputClass} value={recipientName} onChange={(event) => setRecipientName(event.target.value)} /></label>
            <label className="grid gap-1 text-sm font-semibold">{t("customers.phone")}<input className={inputClass} inputMode="tel" value={recipientPhone} onChange={(event) => setRecipientPhone(event.target.value)} /><span className={`text-xs ${normalizedPhone ? "text-emerald-600" : "text-text-muted"}`}>{normalizedPhone ? `${t("fulfillment.normalized")}: ${normalizedPhone}` : t("fulfillment.phoneHint")}</span></label>
            <CitySearchSelect workspaceId={workspaceId} query={city} label={t("fulfillment.city")} onQuery={(value) => { setCity(value); setCityRef(""); setWarehouse(""); setWarehouseRef(""); setWarehouseNumber(""); }} onSelect={(item) => { setCity(item.description); setCityRef(item.ref); setWarehouse(""); setWarehouseRef(""); setWarehouseNumber(""); }} />
            <WarehouseSearchSelect workspaceId={workspaceId} cityRef={cityRef} query={warehouse} label={t("fulfillment.warehouse")} onQuery={(value) => { setWarehouse(value); setWarehouseRef(""); }} onSelect={(item) => { setWarehouse(item.description); setWarehouseRef(item.ref); setWarehouseNumber(item.number || ""); }} />
            <label className="flex items-center gap-2 text-sm font-semibold sm:col-span-2"><input checked={saveAddress} type="checkbox" onChange={(event) => setSaveAddress(event.target.checked)} />{t("fulfillment.saveDefault")}</label>
          </section>
        </> : null}

        {step === 2 ? <>
          <section className="grid gap-3">
            <div className="flex items-center justify-between"><h3 className="font-black">{t("orders.items")}</h3><button className="rounded-xl border border-border-subtle px-3 py-2 text-sm font-bold" type="button" onClick={() => setItems((current) => [...current, emptyItem()])}>{t("actions.addItem")}</button></div>
            {items.map((item) => {
              const stock = inventoryByVariant.get(item.product_variant_id);
              const available = stock ? stock.stock_quantity - stock.reserved_quantity : null;
              return <article className="grid gap-3 rounded-2xl border border-border-subtle p-3 sm:grid-cols-[1fr_110px_140px_auto] sm:items-end" key={item.key}>
                <label className="grid gap-1 text-sm font-semibold">{t("fulfillment.product")}<select className={inputClass} value={item.product_variant_id} onChange={(event) => selectVariant(item, event.target.value)}><option value="">{t("orders.selectVariant")}</option>{variants.filter((variant) => variant.is_active).map((variant) => { const product = productById.get(variant.product_id); const rowStock = inventoryByVariant.get(variant.id); const rowAvailable = rowStock ? rowStock.stock_quantity - rowStock.reserved_quantity : 0; return <option key={variant.id} value={variant.id}>{product?.name || variant.sku} · {variant.sku} · {t("orders.available")}: {rowAvailable}</option>; })}</select>{available != null ? <span className="text-xs text-text-secondary">{t("orders.available")}: {available}</span> : null}</label>
                <label className="grid gap-1 text-sm font-semibold">{t("orders.quantity")}<input className={inputClass} min="1" type="number" value={item.quantity} onChange={(event) => updateItem(item.key, { quantity: event.target.value })} /></label>
                <label className="grid gap-1 text-sm font-semibold">{t("orders.unitPrice")}<input className={inputClass} min="0" step="0.01" type="number" value={item.unit_price} onChange={(event) => updateItem(item.key, { unit_price: event.target.value })} /></label>
                <button className="min-h-11 rounded-xl border border-danger/30 px-3 text-danger disabled:opacity-40" disabled={items.length === 1} type="button" onClick={() => setItems((current) => current.filter((row) => row.key !== item.key))}>×</button>
              </article>;
            })}
          </section>
          <section className="grid gap-3 rounded-2xl border border-border-subtle p-3 sm:grid-cols-3">
            <label className="grid gap-1 text-sm font-semibold">{t("tables.payment")}<select className={inputClass} value={paymentStatus} onChange={(event) => setPaymentStatus(event.target.value as typeof paymentStatus)}>{(["COD", "PAID", "PENDING"] as const).map((value) => <option key={value} value={value}>{formatStatus("payment", value)}</option>)}</select></label>
            {paymentStatus === "COD" ? <label className="grid gap-1 text-sm font-semibold">{t("fulfillment.codAmount")}<input className={inputClass} min="0" type="number" value={codAmount} onChange={(event) => setCodAmount(event.target.value)} /></label> : null}
            <label className="grid gap-1 text-sm font-semibold">{t("fulfillment.declaredValue")}<input className={inputClass} min="0" type="number" value={declaredValue} onChange={(event) => setDeclaredValue(event.target.value)} /></label>
          </section>
          <details className="rounded-2xl border border-border-subtle p-3" open={advancedOpen} onToggle={(event) => setAdvancedOpen(event.currentTarget.open)}><summary className="cursor-pointer font-black">{t("fulfillment.additionalDetails")}</summary><div className="mt-3 grid gap-3 sm:grid-cols-2"><label className="grid gap-1 text-sm font-semibold">{t("orders.campaignLabel")}<select className={inputClass} value={campaignId} onChange={(event) => setCampaignId(event.target.value)}><option value="">{t("orders.noCampaign")}</option>{campaigns.map((campaign) => <option key={campaign.id} value={campaign.id}>{campaign.name}</option>)}</select></label>{[[t("orders.shipping"), shippingCost, setShippingCost], [t("orders.adCost"), adCost, setAdCost], [t("orders.codFee"), codFee, setCodFee], [t("orders.otherCost"), otherCost, setOtherCost]].map(([label, value, setter]) => <label className="grid gap-1 text-sm font-semibold" key={String(label)}>{String(label)}<input className={inputClass} min="0" type="number" value={String(value)} onChange={(event) => (setter as (value: string) => void)(event.target.value)} /></label>)}<label className="grid gap-1 text-sm font-semibold sm:col-span-2">{t("orders.notes")}<textarea className={inputClass} value={notes} onChange={(event) => setNotes(event.target.value)} /></label></div></details>
        </> : null}

        {step === 3 ? <section className="grid gap-4">
          <div className="grid gap-3 rounded-2xl border border-border-subtle p-4 sm:grid-cols-2"><div><span className="text-xs text-text-muted">{t("orders.customerSelector")}</span><strong className="block">{selectedCustomer?.name || customerName}</strong><span className="text-sm text-text-secondary">{normalizedPhone}</span></div><div><span className="text-xs text-text-muted">{t("fulfillment.delivery")}</span><strong className="block">{city}</strong><span className="text-sm text-text-secondary">{warehouse}</span></div><div><span className="text-xs text-text-muted">{t("orders.items")}</span><strong className="block">{items.length}</strong></div><div><span className="text-xs text-text-muted">{t("tables.payment")}</span><strong className="block">{formatStatus("payment", paymentStatus)}</strong></div></div>
          <div className="rounded-2xl bg-surface-2 p-4"><div className="flex items-center justify-between text-lg"><span>{t("fulfillment.total")}</span><strong>{formatMoney(total, currencyCode)}</strong></div>{paymentStatus === "COD" ? <div className="mt-2 flex justify-between text-sm text-text-secondary"><span>{t("fulfillment.codAmount")}</span><span>{formatMoney(codAmount || total, currencyCode)}</span></div> : null}{showProfit ? <div className="mt-2 flex justify-between text-sm text-text-secondary"><span>{t("orders.estimatedProfit")}</span><span>{formatMoney(total - costs, currencyCode)}</span></div> : null}</div>
          {readinessQuery.isLoading ? <div className="rounded-xl border border-blue-300 bg-blue-50 p-3 text-sm font-semibold text-blue-900 dark:border-blue-400/30 dark:bg-blue-500/15 dark:text-blue-100">{t("fulfillment.readinessLoading")}</div> : null}
          {readinessQuery.isError ? <div className="grid gap-2 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-400/30 dark:bg-amber-500/15 dark:text-amber-100" role="alert"><strong>{t("fulfillment.readinessLoadFailed")}</strong><Link className="w-fit font-black underline underline-offset-4" href="/settings/integrations">{t("fulfillment.openIntegrationSettings")}</Link></div> : null}
          {!readinessQuery.isLoading && !readinessQuery.isError && !canCreateTtn ? <div className="grid gap-2 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-400/30 dark:bg-amber-500/15 dark:text-amber-100"><strong>{t("fulfillment.readinessTitle")}</strong><p>{t("fulfillment.readinessHelp")}</p>{writeBlockers.length ? <ul className="list-disc space-y-1 pl-5 font-semibold">{writeBlockers.map((blocker) => <li key={blocker}>{t(`fulfillment.blockers.${blocker}`)}</li>)}</ul> : null}<Link className="w-fit font-black underline underline-offset-4" href="/settings/integrations">{t("fulfillment.openIntegrationSettings")}</Link></div> : null}
          {canCreateTtn ? <div className="rounded-xl border border-emerald-300 bg-emerald-50 p-3 text-sm font-semibold text-emerald-900 dark:border-emerald-400/30 dark:bg-emerald-500/15 dark:text-emerald-100">{t("fulfillment.ready")}</div> : null}
        </section> : null}
      </div>

      {error ? <p className="rounded-xl border border-danger/30 bg-danger/10 px-3 py-2 text-sm font-semibold text-danger" role="alert">{error}</p> : null}
      <footer className="sticky bottom-0 grid gap-2 border-t border-border-subtle bg-surface-1 pt-3 sm:flex sm:justify-between">
        <button className="min-h-11 rounded-xl border border-border-subtle px-4 font-bold disabled:opacity-40" disabled={step === 1 || mutation.isPending} type="button" onClick={() => goTo(step - 1)}>{t("fulfillment.back")}</button>
        {step < 3 ? <button className="min-h-11 rounded-xl bg-primary px-5 font-bold text-primary-foreground" type="button" onClick={() => goTo(step + 1)}>{t("fulfillment.continue")}</button> : <div className="grid gap-2 sm:grid-cols-2"><button className="min-h-11 rounded-xl border border-border-subtle px-4 font-bold disabled:opacity-50" disabled={mutation.isPending} type="button" onClick={() => submit(false)}>{t("fulfillment.createWithoutTtn")}</button><button className="min-h-11 rounded-xl bg-primary px-5 font-bold text-primary-foreground disabled:opacity-50" disabled={!canCreateTtn || mutation.isPending || submitLock.current} type="button" onClick={() => submit(true)}>{mutation.isPending ? t("fulfillment.creating") : t("fulfillment.createOrderAndTtn")}</button></div>}
      </footer>
    </div>
  );
}
