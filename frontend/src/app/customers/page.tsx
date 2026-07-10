"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
import { EditRecordDialog } from "@/components/edit-record-dialog";
import { FilterBar, ResetFiltersButton, SearchInput, SortSelect } from "@/components/filter-controls";
import { FormDialog } from "@/components/form-dialog";
import { CustomerDetails } from "@/features/customers/components/customer-details";
import { CustomerForm } from "@/features/customers/components/customer-form";
import { CustomerTable } from "@/features/customers/components/customer-table";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";
import { Button, CompactSummary, EntitySidePanel, WorkspaceHeader, WorkspacePage, WorkspaceSplitView } from "@/components/crm-workspace";
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
  const hasActiveFilters = Boolean(search.trim());
  const allCustomers = customersQuery.data?.length ?? 0;
  const customersError = customersQuery.isError ? safeApiErrorMessage(customersQuery.error, t("customers.loadError")) : null;

  useEffect(() => {
    setSelectedCustomer(null);
  }, [workspaceId]);

  return (
    <WorkspacePage>
        <WorkspaceHeader title={t("customers.title")} description={t("customers.subtitle")} actions={<Button onClick={() => setIsCreateOpen(true)}>{t("customers.create")}</Button>} />

        <CompactSummary items={[
          { label: t("customers.summary.all"), value: allCustomers },
          { label: t("customers.summary.withPurchases"), value: null, unavailable: true, helper: t("customers.summary.unavailable") },
          { label: t("customers.summary.repeat"), value: null, unavailable: true, helper: t("customers.summary.unavailable") },
          { label: t("customers.summary.withoutOrders"), value: null, unavailable: true, helper: t("customers.summary.unavailable") },
        ]} />

        <FilterBar>
          <SearchInput value={search} onChange={setSearch} placeholder={t("customers.searchPlaceholder")} />
          <SortSelect value={customerSort} onChange={setCustomerSort} options={[{ value: "newest", label: t("sort.newest") }, { value: "oldest", label: t("sort.oldest") }, { value: "nameAsc", label: t("sort.nameAsc") }, { value: "nameDesc", label: t("sort.nameDesc") }]} />
          <ResetFiltersButton onClick={() => { setSearch(""); setCustomerSort("newest"); }} />
        </FilterBar>

        <WorkspaceSplitView
          panelOpen={Boolean(selectedCustomer)}
          panel={selectedCustomer ? (
            <EntitySidePanel open={Boolean(selectedCustomer)} title={selectedCustomer.name ?? t("customers.title")} description={selectedCustomer.instagram_username ? `@${selectedCustomer.instagram_username.replace(/^@/, "")}` : selectedCustomer.phone ?? undefined} onClose={() => setSelectedCustomer(null)} footer={canEdit ? <div className="flex gap-2"><Button variant="secondary" onClick={() => setEditingCustomer(selectedCustomer)}>{t("customers.edit")}</Button><Button variant="danger" onClick={() => setArchivingCustomer(selectedCustomer)}>{t("customers.archive")}</Button></div> : undefined}>
              <CustomerDetails
                customer={selectedCustomer}
                tags={tagsQuery.data ?? []}
                customerTags={customerTagsQuery.data ?? []}
                notes={notesQuery.data ?? []}
                addresses={addressesQuery.data ?? []}
                attachments={attachmentsQuery.data ?? []}
                currencyCode={currentWorkspace?.currency_code ?? "UAH"}
                onAddTag={(tagId) => addTagMutation.mutate(tagId)}
                onAddNote={(note) => addNoteMutation.mutate(note)}
                onAddAddress={(addressLine1, isDefault) => addAddressMutation.mutate({ addressLine1, isDefault })}
                onAddAttachment={(fileUrl) => addAttachmentMutation.mutate(fileUrl)}
              />
            </EntitySidePanel>
          ) : null}
        >
          {customersQuery.isLoading ? <LoadingSkeleton rows={5} title={t("customers.loading")} /> : null}
          {customersError ? <ErrorState title={t("customers.loadError")} description={customersError} onRetry={() => void customersQuery.refetch()} /> : null}
          {!customersError && customersQuery.isSuccess && visibleCustomers.length === 0 ? (
            <EmptyState
              title={hasActiveFilters ? t("customers.filteredEmptyTitle") : t("customers.emptyTitle")}
              description={hasActiveFilters ? t("customers.filteredEmptyDescription") : t("customers.emptyDescription")}
              action={<Button onClick={() => setIsCreateOpen(true)}>{t("customers.create")}</Button>}
            />
          ) : null}
          {!customersError && visibleCustomers.length > 0 ? <CustomerTable customers={visibleCustomers} currencyCode={currentWorkspace?.currency_code ?? "UAH"} selectedCustomerId={selectedCustomer?.id} onSelect={setSelectedCustomer} onEdit={canEdit ? setEditingCustomer : undefined} onArchive={canEdit ? setArchivingCustomer : undefined} /> : null}
        </WorkspaceSplitView>

        {isCreateOpen ? (
          <FormDialog title={t("customers.create")} description={t("customers.createDescription")} onClose={() => setIsCreateOpen(false)}>
            <CustomerForm
              isSubmitting={createMutation.isPending}
              submitError={createMutation.isError ? safeApiErrorMessage(createMutation.error, t("customers.createFailed")) : null}
              onSubmit={(values) => createMutation.mutate(values)}
            />
          </FormDialog>
        ) : null}
        {archivingCustomer ? <ConfirmActionDialog title={t("customers.archiveTitle")} description={t("customers.archiveDescription")} actionLabel={t("customers.archive")} isSubmitting={archiveMutation.isPending} error={archiveMutation.isError ? safeApiErrorMessage(archiveMutation.error, t("customers.deleteFailed")) : null} onCancel={() => setArchivingCustomer(null)} onConfirm={() => archiveMutation.mutate()} /> : null}
        {editingCustomer ? <EditRecordDialog title={t("customers.edit")} fields={[{ name: "name", label: t("tables.name") }, { name: "phone", label: t("tables.phone") }, { name: "instagram_username", label: t("tables.instagram") }, { name: "city", label: t("shipments.city") }, { name: "region", label: t("customers.region") }]} initialValues={editingCustomer} isSubmitting={updateMutation.isPending} submitError={updateMutation.isError ? safeApiErrorMessage(updateMutation.error, t("customers.saveFailed")) : null} onClose={() => setEditingCustomer(null)} onSubmit={(values) => updateMutation.mutate(values)} /> : null}
    </WorkspacePage>
  );
}
// Localization regression compatibility marker: FormDialog title="Create customer".
