"use client";

import { FormEvent, useState } from "react";
import { AddressList } from "@/features/customers/components/address-list";
import { NoteTimeline } from "@/features/customers/components/note-timeline";
import { TagBadge } from "@/features/customers/components/tag-badge";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import { Customer } from "@/types/crm";
import { Attachment, CustomerAddress, CustomerNote, CustomerTag, Tag } from "@/types/crm-completion";

type CustomerDetailsProps = {
  customer: Customer;
  tags: Tag[];
  customerTags: CustomerTag[];
  notes: CustomerNote[];
  addresses: CustomerAddress[];
  attachments: Attachment[];
  currencyCode?: string;
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
  onAddTag,
  onAddNote,
  onAddAddress,
  onAddAttachment,
}: CustomerDetailsProps) {
  const [tagId, setTagId] = useState("");
  const { t } = useI18n();
  const [note, setNote] = useState("");
  const [addressLine1, setAddressLine1] = useState("");
  const [fileUrl, setFileUrl] = useState("");

  function submitNote(event: FormEvent) {
    event.preventDefault();
    if (!note) return;
    onAddNote(note);
    setNote("");
  }

  return (
    <aside className="grid gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-xl font-bold">{customer.name}</h2>
      <section className="grid gap-3 rounded-2xl bg-slate-50 p-3 text-sm sm:grid-cols-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{t("customers.totalOrders")}</p>
          <strong>{customer.total_orders}</strong>
        </div>
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{t("customers.totalSpent")}</p>
          <strong>{formatMoney(customer.total_spent, currencyCode)}</strong>
        </div>
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{t("customers.lastOrder")}</p>
          <strong>{customer.last_order_at ? new Date(customer.last_order_at).toLocaleDateString() : "—"}</strong>
        </div>
      </section>
      <section className="rounded-2xl border border-slate-100 p-3 text-sm">
        <h3 className="font-semibold">{t("customers.contact")}</h3>
        <p className="mt-2">{t("tables.phone")}: {customer.phone ?? "—"}</p>
        <p>{t("tables.instagram")}: {customer.instagram_username ? `@${customer.instagram_username.replace(/^@/, "")}` : "—"}</p>
        <p>{t("shipments.city")}: {[customer.city, customer.region].filter(Boolean).join(", ") || "—"}</p>
      </section>

      <section>
        <h3 className="font-semibold">{t("customers.tags")}</h3>
        <div className="my-2 flex flex-wrap gap-2">
          {customerTags.map((item) => (item.tag ? <TagBadge key={item.id} tag={item.tag} /> : null))}
        </div>
        <div className="flex gap-2">
          <select
            className="min-w-0 flex-1 rounded-md border border-slate-300 px-2 py-1"
            value={tagId}
            onChange={(event) => setTagId(event.target.value)}
          >
            <option value="">{t("customers.selectTag")}</option>
            {tags.map((tag) => (
              <option key={tag.id} value={tag.id}>{tag.name}</option>
            ))}
          </select>
          <button className="rounded bg-blue-600 px-3 py-1 text-white" onClick={() => tagId && onAddTag(tagId)}>
            {t("customers.add")}
          </button>
        </div>
      </section>

      <section>
        <h3 className="font-semibold">{t("customers.notesTimeline")}</h3>
        <NoteTimeline notes={notes} />
        <form className="mt-2 flex gap-2" onSubmit={submitNote}>
          <input
            className="min-w-0 flex-1 rounded-md border border-slate-300 px-2 py-1"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder={t("customers.appendNote")}
          />
          <button className="rounded bg-blue-600 px-3 py-1 text-white">{t("customers.add")}</button>
        </form>
      </section>

      <section>
        <h3 className="font-semibold">{t("customers.addresses")}</h3>
        <AddressList addresses={addresses} />
        <div className="mt-2 flex gap-2">
          <input
            className="min-w-0 flex-1 rounded-md border border-slate-300 px-2 py-1"
            value={addressLine1}
            onChange={(event) => setAddressLine1(event.target.value)}
            placeholder={t("customers.addressLine")}
          />
          <button
            className="rounded bg-blue-600 px-3 py-1 text-white"
            onClick={() => {
              if (!addressLine1) return;
              onAddAddress(addressLine1, addresses.length === 0);
              setAddressLine1("");
            }}
          >
            {t("customers.add")}
          </button>
        </div>
      </section>

      <section>
        <h3 className="font-semibold">{t("customers.attachments")}</h3>
        {attachments.map((attachment) => (
          <a key={attachment.id} className="block text-sm text-blue-600" href={attachment.file_url}>
            {attachment.file_name ?? attachment.file_url}
          </a>
        ))}
        <div className="mt-2 flex gap-2">
          <input
            className="min-w-0 flex-1 rounded-md border border-slate-300 px-2 py-1"
            value={fileUrl}
            onChange={(event) => setFileUrl(event.target.value)}
            placeholder={t("customers.fileUrl")}
          />
          <button
            className="rounded bg-blue-600 px-3 py-1 text-white"
            onClick={() => {
              if (!fileUrl) return;
              onAddAttachment(fileUrl);
              setFileUrl("");
            }}
          >
            {t("customers.add")}
          </button>
        </div>
      </section>
    </aside>
  );
}
