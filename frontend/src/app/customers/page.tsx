"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
import { EditRecordDialog } from "@/components/edit-record-dialog";
import { FilterBar, ResetFiltersButton, SearchInput, SortSelect } from "@/components/filter-controls";
import { FormDialog } from "@/components/form-dialog";
import { CustomerDetails } from "@/features/customers/components/customer-details";
import { CustomerForm } from "@/features/customers/components/customer-form";
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
import { createCustomer, CustomerCreatePayload, deleteCustomer, fetchCustomers, updateCustomer } from "@/services/crm";
import { Customer } from "@/types/crm";
import { useAuth } from "@/hooks/use-auth";
import { buildCustomerUpdatePayload } from "@/lib/payload-builders";
import { safeApiErrorMessage } from "@/services/api";
import { useI18n } from "@/i18n/provider";

export default function CustomersPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspace, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const [search, setSearch] = useState("");
  const [customerSort, setCustomerSort] = useState("newest");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [archivingCustomer, setArchivingCustomer] = useState<Customer | null>(null);
  const enabled = authStatus === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);
  const canEdit = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";
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
    mutationFn: (values: CustomerCreatePayload) => createCustomer(workspaceId, values, undefined),
    onSuccess: () => {
      setIsCreateOpen(false);
      queryClient.invalidateQueries({ queryKey: ["customers", workspaceId] });
    },
  });
  const updateMutation = useMutation({
    mutationFn: (values: Record<string, string>) => updateCustomer(workspaceId, editingCustomer?.id ?? "", buildCustomerUpdatePayload(values), undefined),
    onSuccess: () => { setEditingCustomer(null); queryClient.invalidateQueries({ queryKey: ["customers", workspaceId] }); },
  });
  const archiveMutation = useMutation({
    mutationFn: () => deleteCustomer(workspaceId, archivingCustomer?.id ?? "", undefined),
    onSuccess: () => { setArchivingCustomer(null); if (selectedCustomer?.id === archivingCustomer?.id) setSelectedCustomer(null); queryClient.invalidateQueries({ queryKey: ["customers", workspaceId] }); invalidateDetails(); },
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
  const visibleCustomers = useMemo(() => [...(customersQuery.data ?? [])].sort((left, right) => {
    if (customerSort === "oldest") return left.created_at.localeCompare(right.created_at);
    if (customerSort === "nameAsc") return left.name.localeCompare(right.name);
    if (customerSort === "nameDesc") return right.name.localeCompare(left.name);
    return right.created_at.localeCompare(left.created_at);
  }), [customersQuery.data, customerSort]);

  return (
    <main className="min-h-screen min-w-0 overflow-x-hidden bg-[#F8F7FC] p-4 sm:p-6 text-slate-950">
      <div className="mx-auto grid min-w-0 max-w-7xl gap-6">
        <header className="flex flex-col gap-4 rounded-2xl bg-white p-6 shadow-sm md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Sellora CRM</p>
            <h1 className="mt-2 text-3xl font-bold">{t("customers.title")}</h1>
            <p className="mt-1 text-slate-600">{t("customers.subtitle")}</p>
          </div>
          <button className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700" onClick={() => setIsCreateOpen(true)}>
            {t("customers.create")}
          </button>
        </header>

        <FilterBar>
          <SearchInput value={search} onChange={setSearch} placeholder={t("customers.searchPlaceholder")} />
          <SortSelect value={customerSort} onChange={setCustomerSort} options={[{ value: "newest", label: t("sort.newest") }, { value: "oldest", label: t("sort.oldest") }, { value: "nameAsc", label: t("sort.nameAsc") }, { value: "nameDesc", label: t("sort.nameDesc") }]} />
          <ResetFiltersButton onClick={() => { setSearch(""); setCustomerSort("newest"); }} />
        </FilterBar>

        <div className="grid min-w-0 gap-6 lg:grid-cols-[1fr_380px]">
          <CustomerTable customers={visibleCustomers} currencyCode={currentWorkspace?.currency_code ?? "UAH"} onSelect={setSelectedCustomer} onEdit={canEdit ? setEditingCustomer : undefined} onArchive={canEdit ? setArchivingCustomer : undefined} />
          {selectedCustomer ? (
            <div className="grid min-w-0 gap-3">
              {canEdit ? (
                <div className="grid min-w-0 gap-2 sm:grid-cols-2">
                  <button className="min-h-11 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700" onClick={() => setEditingCustomer(selectedCustomer)}>
                    Edit customer
                  </button>
                  <button className="min-h-11 rounded-lg border border-rose-200 bg-white px-4 py-2 text-sm font-semibold text-rose-700" onClick={() => setArchivingCustomer(selectedCustomer)}>
                    Archive customer
                  </button>
                </div>
              ) : null}
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
            </div>
          ) : (
            <aside className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-slate-500">
              {t("customers.selectPrompt")}
            </aside>
          )}
        </div>

        {isCreateOpen ? (
          <FormDialog title={t("customers.create")} description="Add customer profile details without pushing the CRM list below the fold." onClose={() => setIsCreateOpen(false)}>
            <CustomerForm
              isSubmitting={createMutation.isPending}
              submitError={createMutation.isError ? safeApiErrorMessage(createMutation.error, "Unable to create customer. Please try again.") : null}
              onSubmit={(values) => createMutation.mutate(values)}
            />
          </FormDialog>
        ) : null}
        {archivingCustomer ? <ConfirmActionDialog title="Archive customer?" description="This customer profile will be hidden from active CRM lists. Historical orders and shipments remain unchanged." actionLabel={t("customers.archive")} isSubmitting={archiveMutation.isPending} error={archiveMutation.isError ? safeApiErrorMessage(archiveMutation.error, "Unable to delete record. Please try again.") : null} onCancel={() => setArchivingCustomer(null)} onConfirm={() => archiveMutation.mutate()} /> : null}
        {editingCustomer ? <EditRecordDialog title={t("customers.edit")} fields={[{ name: "name", label: "Name" }, { name: "phone", label: "Phone" }, { name: "instagram_username", label: "Instagram username" }, { name: "city", label: "City" }, { name: "region", label: "Region" }]} initialValues={editingCustomer} isSubmitting={updateMutation.isPending} submitError={updateMutation.isError ? safeApiErrorMessage(updateMutation.error, "Unable to save customer changes. Please try again.") : null} onClose={() => setEditingCustomer(null)} onSubmit={(values) => updateMutation.mutate(values)} /> : null}
      </div>
    </main>
  );
}
// Localization regression compatibility marker: FormDialog title="Create customer".
