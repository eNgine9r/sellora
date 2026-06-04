"use client";

import { FormEvent, useState } from "react";
import { AddressList } from "@/features/customers/components/address-list";
import { NoteTimeline } from "@/features/customers/components/note-timeline";
import { TagBadge } from "@/features/customers/components/tag-badge";
import { Customer } from "@/types/crm";
import { Attachment, CustomerAddress, CustomerNote, CustomerTag, Tag } from "@/types/crm-completion";

type CustomerDetailsProps = {
  customer: Customer;
  tags: Tag[];
  customerTags: CustomerTag[];
  notes: CustomerNote[];
  addresses: CustomerAddress[];
  attachments: Attachment[];
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
  onAddTag,
  onAddNote,
  onAddAddress,
  onAddAttachment,
}: CustomerDetailsProps) {
  const [tagId, setTagId] = useState("");
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

      <section>
        <h3 className="font-semibold">Tags</h3>
        <div className="my-2 flex flex-wrap gap-2">
          {customerTags.map((item) => (item.tag ? <TagBadge key={item.id} tag={item.tag} /> : null))}
        </div>
        <div className="flex gap-2">
          <select
            className="min-w-0 flex-1 rounded-md border border-slate-300 px-2 py-1"
            value={tagId}
            onChange={(event) => setTagId(event.target.value)}
          >
            <option value="">Select tag</option>
            {tags.map((tag) => (
              <option key={tag.id} value={tag.id}>{tag.name}</option>
            ))}
          </select>
          <button className="rounded bg-blue-600 px-3 py-1 text-white" onClick={() => tagId && onAddTag(tagId)}>
            Add
          </button>
        </div>
      </section>

      <section>
        <h3 className="font-semibold">Notes timeline</h3>
        <NoteTimeline notes={notes} />
        <form className="mt-2 flex gap-2" onSubmit={submitNote}>
          <input
            className="min-w-0 flex-1 rounded-md border border-slate-300 px-2 py-1"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Append note"
          />
          <button className="rounded bg-blue-600 px-3 py-1 text-white">Add</button>
        </form>
      </section>

      <section>
        <h3 className="font-semibold">Addresses</h3>
        <AddressList addresses={addresses} />
        <div className="mt-2 flex gap-2">
          <input
            className="min-w-0 flex-1 rounded-md border border-slate-300 px-2 py-1"
            value={addressLine1}
            onChange={(event) => setAddressLine1(event.target.value)}
            placeholder="Address line"
          />
          <button
            className="rounded bg-blue-600 px-3 py-1 text-white"
            onClick={() => {
              if (!addressLine1) return;
              onAddAddress(addressLine1, addresses.length === 0);
              setAddressLine1("");
            }}
          >
            Add
          </button>
        </div>
      </section>

      <section>
        <h3 className="font-semibold">Attachments</h3>
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
            placeholder="File URL"
          />
          <button
            className="rounded bg-blue-600 px-3 py-1 text-white"
            onClick={() => {
              if (!fileUrl) return;
              onAddAttachment(fileUrl);
              setFileUrl("");
            }}
          >
            Add
          </button>
        </div>
      </section>
    </aside>
  );
}
