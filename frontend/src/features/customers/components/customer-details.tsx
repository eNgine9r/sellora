"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { DrawerTabs } from "@/components/crm-workspace";
import { AddressList } from "@/features/customers/components/address-list";
import { NoteTimeline } from "@/features/customers/components/note-timeline";
import { TagBadge } from "@/features/customers/components/tag-badge";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import { Customer } from "@/types/crm";
import { CustomerOrderSummary } from "@/services/crm";
import { Attachment, CustomerAddress, CustomerNote, CustomerTag, Tag } from "@/types/crm-completion";

type CustomerDetailsProps = {
  customer: Customer;
  tags: Tag[];
  customerTags: CustomerTag[];
  notes: CustomerNote[];
  addresses: CustomerAddress[];
  attachments: Attachment[];
  currencyCode?: string;
  orders: CustomerOrderSummary[];
  ordersLoading: boolean;
  ordersError: boolean;
  onAddTag: (tagId: string) => void;
  onAddNote: (note: string) => void;
  onAddAddress: (addressLine1: string, isDefault: boolean) => void;
  onAddAttachment: (fileUrl: string) => void;
};

export function CustomerDetails({
  customer,
  tags,
  customerTags,
  notes,
  addresses,
  attachments,
  currencyCode = "UAH",
  orders,
  ordersLoading,
  ordersError,
  onAddTag,
  onAddNote,
  onAddAddress,
  onAddAttachment,
}: CustomerDetailsProps) {
  const [tagId, setTagId] = useState("");
  const { t, formatStatus } = useI18n();
  const [note, setNote] = useState("");
  const [addressLine1, setAddressLine1] = useState("");
  const [fileUrl, setFileUrl] = useState("");
  const [activeTab, setActiveTab] = useState("overview");
  const tabs = [
    { id: "overview", label: t("customers.tabs.overview") },
    { id: "orders", label: t("customers.tabs.orders") },
    { id: "notes", label: t("customers.tabs.notes") },
    { id: "addresses", label: t("customers.tabs.addresses") },
    { id: "activity", label: t("customers.tabs.activity") },
  ];

  function submitNote(event: FormEvent) {
    event.preventDefault();
    if (!note) return;
    onAddNote(note);
    setNote("");
  }

  return (
    <aside className="grid gap-4 rounded-[var(--radius-card)] border border-border-subtle bg-surface-1 p-0 shadow-none">
      <h2 className="sr-only">{customer.name}</h2>
      <DrawerTabs tabs={tabs} active={activeTab} onChange={setActiveTab} />
      {activeTab === "overview" ? <>
      <section className="grid gap-3 rounded-2xl bg-surface-2 p-3 text-sm sm:grid-cols-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-text-muted">{t("customers.totalOrders")}</p>
          <strong>{customer.total_orders}</strong>
        </div>
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-text-muted">{t("customers.paidPurchases")}</p>
          <strong>{customer.paid_orders}</strong>
        </div>
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-text-muted">{t("customers.paidSpent")}</p>
          <strong>{formatMoney(customer.total_spent, currencyCode)}</strong>
        </div>
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-text-muted">{t("customers.lastOrder")}</p>
          <strong>{customer.last_order_at ? new Date(customer.last_order_at).toLocaleDateString() : "—"}</strong>
        </div>
      </section>
      <p className="text-xs text-text-muted">{t("customers.verifiedSpendingHint")}</p>
      {customer.unpriced_orders > 0 ? <p className="rounded-lg bg-amber-500/10 p-2.5 text-xs font-semibold text-amber-600">{t("customers.unpricedOrders")}: {customer.unpriced_orders}. {t("customers.unpricedHint")}</p> : null}
      <section className="rounded-2xl border border-border-subtle bg-surface-2 p-3 text-sm">
        <h3 className="font-semibold text-text-primary">{t("customers.lastOrder")}</h3>
        {customer.last_order_number ? (
          <>
            <p className="mt-1 font-semibold text-text-primary">{customer.last_order_number}</p>
            <p className="text-text-muted">{customer.last_order_status ? formatStatus("order", customer.last_order_status) : "—"} · {customer.last_order_payment_status ? formatStatus("payment", customer.last_order_payment_status) : "—"}</p>
          </>
        ) : <p className="mt-1 text-text-muted">{t("customers.noLinkedOrders")}</p>}
      </section>
      <section className="rounded-2xl border border-border-subtle bg-surface-2 p-3 text-sm">
        <h3 className="font-semibold text-text-primary">{t("customers.contact")}</h3>
        <p className="mt-2">{t("tables.phone")}: {customer.phone ?? "—"}</p>
        <p>{t("tables.instagram")}: {customer.instagram_username ? `@${customer.instagram_username.replace(/^@/, "")}` : "—"}</p>
        <p>{t("shipments.city")}: {[customer.city, customer.region].filter(Boolean).join(", ") || "—"}</p>
        <p>{t("customers.source")}: {t(`customers.sources.${customer.source}`)}</p>
        {customer.source_direct_conversation_id ? (
          <Link href={`/direct?conversation=${encodeURIComponent(customer.source_direct_conversation_id)}`} className="mt-2 inline-flex min-h-10 items-center rounded-xl px-3 font-semibold text-primary hover:bg-primary/10">{t("customers.openDirect")}</Link>
        ) : null}
      </section>

      <section>
        <h3 className="font-semibold text-text-primary">{t("customers.tags")}</h3>
        <div className="my-2 flex flex-wrap gap-2">
          {customerTags.map((item) => (item.tag ? <TagBadge key={item.id} tag={item.tag} /> : null))}
        </div>
        <div className="flex gap-2">
          <select
            className="min-w-0 flex-1 rounded-xl border border-input-border bg-input-background px-3 py-2 text-text-primary"
            value={tagId}
            onChange={(event) => setTagId(event.target.value)}
          >
            <option value="">{t("customers.selectTag")}</option>
            {tags.map((tag) => (
              <option key={tag.id} value={tag.id}>{tag.name}</option>
            ))}
          </select>
          <button className="rounded-xl bg-primary px-3 py-2 font-bold text-primary-foreground" onClick={() => tagId && onAddTag(tagId)}>
            {t("customers.add")}
          </button>
        </div>
      </section>

      </> : null}

      {activeTab === "orders" ? (
        <section className="grid gap-2">
          <h3 className="font-semibold text-text-primary">{t("customers.tabs.orders")} · {customer.total_orders}</h3>
          {ordersLoading ? <p className="text-sm text-text-muted">{t("customers.loadingOrders")}</p> : null}
          {ordersError ? <p role="alert" className="text-sm text-danger">{t("customers.ordersLoadFailed")}</p> : null}
          {!ordersLoading && !ordersError && orders.length === 0 ? <p className="text-sm text-text-muted">{t("customers.noLinkedOrders")}</p> : null}
          {!ordersError && orders.map((order) => (
            <article key={order.id} className="rounded-2xl border border-border-subtle bg-surface-2 p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <strong className="break-all text-text-primary">{order.order_number}</strong>
                <span className="text-xs text-text-muted">{new Date(order.created_at).toLocaleDateString("uk-UA")}</span>
              </div>
              <p className="mt-1 text-text-secondary">{t("customers.orderStatus")}: {formatStatus("order", order.status)}</p>
              <p className="text-text-secondary">{t("customers.payment")}: {formatStatus("payment", order.payment_status)}</p>
              <p className="text-text-secondary">{t("customers.orderValue")}: {order.is_historical && Number(order.revenue) === 0 ? t("orders.unknownAmount") : formatMoney(order.revenue, currencyCode)}</p>
              {order.shipment_tracking ? <p className="mt-1 break-all text-text-secondary">{t("customers.tracking")}: {order.shipment_tracking} · {order.shipment_status ? formatStatus("shipment", order.shipment_status) : "—"}</p> : null}
              {order.shipment_city ? <p className="text-xs text-text-muted">{order.shipment_city}</p> : null}
            </article>
          ))}
          {customer.total_orders > orders.length ? <p className="text-xs text-text-muted">{t("customers.ordersPreviewLimit")}</p> : null}
          <p className="text-xs text-text-muted">{t("customers.unlinkedHistoryNotice")}</p>
        </section>
      ) : null}

      {activeTab === "notes" ? <section>
        <h3 className="font-semibold text-text-primary">{t("customers.notesTimeline")}</h3>
        <NoteTimeline notes={notes} />
        <form className="mt-2 flex gap-2" onSubmit={submitNote}>
          <input
            className="min-w-0 flex-1 rounded-xl border border-input-border bg-input-background px-3 py-2 text-text-primary"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder={t("customers.appendNote")}
          />
          <button className="rounded-xl bg-primary px-3 py-2 font-bold text-primary-foreground">{t("customers.add")}</button>
        </form>
      </section> : null}

      {activeTab === "addresses" ? <section>
        <h3 className="font-semibold text-text-primary">{t("customers.addresses")}</h3>
        <AddressList addresses={addresses} />
        <div className="mt-2 flex gap-2">
          <input
            className="min-w-0 flex-1 rounded-xl border border-input-border bg-input-background px-3 py-2 text-text-primary"
            value={addressLine1}
            onChange={(event) => setAddressLine1(event.target.value)}
            placeholder={t("customers.addressLine")}
          />
          <button
            className="rounded-xl bg-primary px-3 py-2 font-bold text-primary-foreground"
            onClick={() => {
              if (!addressLine1) return;
              onAddAddress(addressLine1, addresses.length === 0);
              setAddressLine1("");
            }}
          >
            {t("customers.add")}
          </button>
        </div>
      </section> : null}

      {activeTab === "activity" ? <section>
        <h3 className="font-semibold text-text-primary">{t("customers.attachments")}</h3>
        {attachments.map((attachment) => (
          <a key={attachment.id} className="block break-words text-sm font-semibold text-primary" href={attachment.file_url}>
            {attachment.file_name ?? attachment.file_url}
          </a>
        ))}
        <div className="mt-2 flex gap-2">
          <input
            className="min-w-0 flex-1 rounded-xl border border-input-border bg-input-background px-3 py-2 text-text-primary"
            value={fileUrl}
            onChange={(event) => setFileUrl(event.target.value)}
            placeholder={t("customers.fileUrl")}
          />
          <button
            className="rounded-xl bg-primary px-3 py-2 font-bold text-primary-foreground"
            onClick={() => {
              if (!fileUrl) return;
              onAddAttachment(fileUrl);
              setFileUrl("");
            }}
          >
            {t("customers.add")}
          </button>
        </div>
      </section> : null}
    </aside>
  );
}
