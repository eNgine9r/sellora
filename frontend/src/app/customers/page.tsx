"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { CustomerDetails } from "@/features/customers/components/customer-details";
import { CustomerForm, CustomerFormValues } from "@/features/customers/components/customer-form";
import { CustomerTable } from "@/features/customers/components/customer-table";
import {
  addAttachment,
  addCustomerAddress,
  addCustomerNote,
  addCustomerTag,
  fetchAttachments,
  fetchCustomerAddresses,
  fetchCustomerNotes,
  fetchCustomerTags,
  fetchTags,
} from "@/services/crm-completion";
import { createCustomer, fetchCustomers } from "@/services/crm";
import { Customer } from "@/types/crm";
import { useAuth } from "@/hooks/use-auth";

export default function CustomersPage() {
  const queryClient = useQueryClient();
  const { currentWorkspaceId } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const [search, setSearch] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const enabled = Boolean(workspaceId);
  const selectedId = selectedCustomer?.id ?? "";

  const customersQuery = useQuery({
    queryKey: ["customers", workspaceId, search],
    queryFn: () => fetchCustomers(workspaceId, search, undefined),
    enabled,
  });
  const tagsQuery = useQuery({
    queryKey: ["tags", workspaceId],
    queryFn: () => fetchTags(workspaceId, undefined),
    enabled,
  });
  const customerTagsQuery = useQuery({
    queryKey: ["customer-tags", workspaceId, selectedId],
    queryFn: () => fetchCustomerTags(workspaceId, selectedId, undefined),
    enabled: enabled && Boolean(selectedId),
  });
  const notesQuery = useQuery({
    queryKey: ["customer-notes", workspaceId, selectedId],
    queryFn: () => fetchCustomerNotes(workspaceId, selectedId, undefined),
    enabled: enabled && Boolean(selectedId),
  });
  const addressesQuery = useQuery({
    queryKey: ["customer-addresses", workspaceId, selectedId],
    queryFn: () => fetchCustomerAddresses(workspaceId, selectedId, undefined),
    enabled: enabled && Boolean(selectedId),
  });
  const attachmentsQuery = useQuery({
    queryKey: ["customer-attachments", workspaceId, selectedId],
    queryFn: () => fetchAttachments(workspaceId, "CUSTOMER", selectedId, undefined),
    enabled: enabled && Boolean(selectedId),
  });

  const invalidateDetails = () => {
    queryClient.invalidateQueries({ queryKey: ["customer-tags", workspaceId, selectedId] });
    queryClient.invalidateQueries({ queryKey: ["customer-notes", workspaceId, selectedId] });
    queryClient.invalidateQueries({ queryKey: ["customer-addresses", workspaceId, selectedId] });
    queryClient.invalidateQueries({ queryKey: ["customer-attachments", workspaceId, selectedId] });
  };

  const createMutation = useMutation({
    mutationFn: (values: CustomerFormValues) => createCustomer(workspaceId, values, undefined),
    onSuccess: () => {
      setIsCreateOpen(false);
      queryClient.invalidateQueries({ queryKey: ["customers", workspaceId] });
    },
  });
  const addTagMutation = useMutation({
    mutationFn: (tagId: string) => addCustomerTag(workspaceId, selectedId, tagId, undefined),
    onSuccess: invalidateDetails,
  });
  const addNoteMutation = useMutation({
    mutationFn: (note: string) => addCustomerNote(workspaceId, selectedId, note, undefined),
    onSuccess: invalidateDetails,
  });
  const addAddressMutation = useMutation({
    mutationFn: ({ addressLine1, isDefault }: { addressLine1: string; isDefault: boolean }) =>
      addCustomerAddress(workspaceId, selectedId, { address_line1: addressLine1, is_default: isDefault }, undefined),
    onSuccess: invalidateDetails,
  });
  const addAttachmentMutation = useMutation({
    mutationFn: (fileUrl: string) =>
      addAttachment(workspaceId, { entity_type: "CUSTOMER", entity_id: selectedId, file_url: fileUrl }, undefined),
    onSuccess: invalidateDetails,
  });

  return (
    <main className="min-h-screen bg-[#F8F7FC] p-4 sm:p-6 text-slate-950">
      <div className="mx-auto grid max-w-7xl gap-6">
        <header className="flex flex-col gap-4 rounded-2xl bg-white p-6 shadow-sm md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Sellora CRM</p>
            <h1 className="mt-2 text-3xl font-bold">Customers</h1>
            <p className="mt-1 text-slate-600">Manage customers, notes, tags, addresses, and attachments.</p>
          </div>
          <button className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700" onClick={() => setIsCreateOpen(true)}>
            Create customer
          </button>
        </header>

        <section className="grid gap-3 rounded-2xl bg-white p-4 shadow-sm md:grid-cols-3">
          <input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Search customers" value={search} onChange={(event) => setSearch(event.target.value)} />
        </section>

        <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
          <CustomerTable customers={customersQuery.data ?? []} onSelect={setSelectedCustomer} />
          {selectedCustomer ? (
            <CustomerDetails
              customer={selectedCustomer}
              tags={tagsQuery.data ?? []}
              customerTags={customerTagsQuery.data ?? []}
              notes={notesQuery.data ?? []}
              addresses={addressesQuery.data ?? []}
              attachments={attachmentsQuery.data ?? []}
              onAddTag={(tagId) => addTagMutation.mutate(tagId)}
              onAddNote={(note) => addNoteMutation.mutate(note)}
              onAddAddress={(addressLine1, isDefault) => addAddressMutation.mutate({ addressLine1, isDefault })}
              onAddAttachment={(fileUrl) => addAttachmentMutation.mutate(fileUrl)}
            />
          ) : (
            <aside className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-slate-500">
              Select a customer to manage CRM details.
            </aside>
          )}
        </div>

        {isCreateOpen ? (
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <CustomerForm onSubmit={(values) => createMutation.mutate(values)} />
          </div>
        ) : null}
      </div>
    </main>
  );
}
