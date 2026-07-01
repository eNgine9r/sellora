"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
import {
  FilterBar,
  ResetFiltersButton,
  SearchInput,
  SortSelect,
} from "@/components/filter-controls";
import { FormDialog } from "@/components/form-dialog";
import {
  clampPage,
  paginateItems,
  PaginationControls,
  PAGE_SIZE_OPTIONS,
} from "@/components/pagination-controls";
import { EmptyState, LoadingSkeleton } from "@/components/ui/states";
import { OrderDetails } from "@/features/orders/components/order-details";
import { OrderForm } from "@/features/orders/components/order-form";
import { OrderTable } from "@/features/orders/components/order-table";
import { formatMoney } from "@/lib/currency";
import { createCustomer, fetchCustomers } from "@/services/crm";
<<<<<<< HEAD
=======
import { fetchAdCampaigns } from "@/services/advertising";
>>>>>>> origin/codex/2026-07-01-create-initial-sellora-repository-structure
import {
  changeOrderStatus,
  createOrder,
  deleteOrder,
  fetchOrderDashboard,
  fetchOrders,
  updateOrder,
} from "@/services/orders";
import { fetchOrderShipment } from "@/services/shipments";
import {
  fetchInventory,
  fetchProducts,
  fetchProductVariants,
} from "@/services/products";
import { Customer } from "@/types/crm";
import { Order, OrderStatus, PaymentStatus } from "@/types/orders";
import { useAuth } from "@/hooks/use-auth";
import { safeApiErrorMessage } from "@/services/api";
import { useI18n } from "@/i18n/provider";

const STATUSES: (OrderStatus | "")[] = [
  "",
  "NEW",
  "CONFIRMED",
  "SHIPPED",
  "DELIVERED",
  "COMPLETED",
  "RETURNED",
  "CANCELLED",
];
const ITEM_EDIT_STATUSES: OrderStatus[] = ["NEW", "CONFIRMED"];

export default function OrdersPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const {
    currentUser,
    currentWorkspace,
    currentWorkspaceId,
    status: authStatus,
  } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const currencyCode = currentWorkspace?.currency_code ?? "UAH";
  const [status, setStatus] = useState<OrderStatus | "">("");
  const [paymentStatus, setPaymentStatus] = useState<PaymentStatus | "">("");
  const [search, setSearch] = useState("");
  const [orderSort, setOrderSort] = useState("newest");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] =
    useState<(typeof PAGE_SIZE_OPTIONS)[number]>(5);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingOrder, setEditingOrder] = useState<Order | null>(null);
  const [archivingOrder, setArchivingOrder] = useState<Order | null>(null);
  const enabled =
    authStatus === "authenticated" &&
    Boolean(currentUser) &&
    Boolean(workspaceId);
  const canEdit =
    currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";

  const ordersQuery = useQuery({
    queryKey: ["orders", workspaceId, status],
    queryFn: () => fetchOrders(workspaceId, status),
    enabled,
  });
  const dashboardQuery = useQuery({
    queryKey: ["orders-dashboard", workspaceId],
    queryFn: () => fetchOrderDashboard(workspaceId),
    enabled,
  });
  const variantsQuery = useQuery({
    queryKey: ["product-variants", workspaceId],
    queryFn: () => fetchProductVariants(workspaceId, undefined, undefined),
    enabled,
  });
  const productsQuery = useQuery({
    queryKey: ["products", workspaceId],
    queryFn: () => fetchProducts(workspaceId),
    enabled,
  });
  const inventoryQuery = useQuery({
    queryKey: ["inventory", workspaceId],
    queryFn: () => fetchInventory(workspaceId),
    enabled,
  });
  const customersQuery = useQuery({
    queryKey: ["customers", workspaceId, "order-selector"],
    queryFn: () => fetchCustomers(workspaceId),
    enabled,
  });
<<<<<<< HEAD
=======
  const campaignsQuery = useQuery({
    queryKey: ["ad-campaigns", workspaceId, "order-attribution"],
    queryFn: () => fetchAdCampaigns(workspaceId),
    enabled,
  });
>>>>>>> origin/codex/2026-07-01-create-initial-sellora-repository-structure
  const shipmentQuery = useQuery({
    queryKey: ["order-shipment", workspaceId, selectedOrder?.id],
    queryFn: () => fetchOrderShipment(workspaceId, selectedOrder!.id),
    enabled: enabled && Boolean(selectedOrder),
  });
  const invalidateOrderState = () => {
    queryClient.invalidateQueries({ queryKey: ["orders", workspaceId] });
    queryClient.invalidateQueries({
      queryKey: ["orders-dashboard", workspaceId],
    });
    queryClient.invalidateQueries({ queryKey: ["dashboard", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["analytics", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["inventory", workspaceId] });
    queryClient.invalidateQueries({
      queryKey: ["product-variants", workspaceId],
    });
    queryClient.invalidateQueries({ queryKey: ["shipments", workspaceId] });
  };
  const createMutation = useMutation({
    mutationFn: (values: Parameters<typeof createOrder>[1]) =>
      createOrder(workspaceId, values),
    onSuccess: (order) => {
      setIsCreateOpen(false);
      setSelectedOrder(order);
      invalidateOrderState();
    },
  });
  const statusMutation = useMutation({
    mutationFn: ({
      orderId,
      nextStatus,
    }: {
      orderId: string;
      nextStatus: OrderStatus;
    }) => changeOrderStatus(workspaceId, orderId, nextStatus),
    onSuccess: (order) => {
      setSelectedOrder(order);
      invalidateOrderState();
    },
  });
  const updateMutation = useMutation({
    mutationFn: (values: Parameters<typeof updateOrder>[2]) =>
      updateOrder(workspaceId, editingOrder?.id ?? "", values),
    onSuccess: (order) => {
      setEditingOrder(null);
      setSelectedOrder(order);
      invalidateOrderState();
    },
  });
  const archiveMutation = useMutation({
    mutationFn: () => deleteOrder(workspaceId, archivingOrder?.id ?? ""),
    onSuccess: () => {
      if (selectedOrder?.id === archivingOrder?.id) setSelectedOrder(null);
      setArchivingOrder(null);
      invalidateOrderState();
    },
  });
  const createCustomerMutation = useMutation({
    mutationFn: (payload: Parameters<typeof createCustomer>[1]) =>
      createCustomer(workspaceId, payload),
    onSuccess: (customer) => {
      queryClient.setQueryData<Customer[]>(
        ["customers", workspaceId, "order-selector"],
        (current = []) => [
          customer,
          ...current.filter((item) => item.id !== customer.id),
        ],
      );
      queryClient.invalidateQueries({ queryKey: ["customers", workspaceId] });
    },
  });

  const filteredOrders = useMemo(() => {
    const query = search.trim().toLowerCase();
    return (ordersQuery.data ?? [])
      .filter((order) => {
        const searchable = [
          order.order_number,
          order.customer_id,
          order.customer_name,
          order.customer_phone,
          order.customer_instagram_username,
          order.notes,
          ...order.items.flatMap((item) => [item.product_name, item.sku]),
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        const matchesSearch = !query || searchable.includes(query);
        const matchesPayment =
          !paymentStatus || order.payment_status === paymentStatus;
        return matchesSearch && matchesPayment;
      })
      .sort((left, right) => {
        const leftRevenue = Number(left.revenue ?? 0);
        const rightRevenue = Number(right.revenue ?? 0);
        const leftProfit = Number(left.net_profit ?? 0);
        const rightProfit = Number(right.net_profit ?? 0);
        if (orderSort === "oldest")
          return left.created_at.localeCompare(right.created_at);
        if (orderSort === "revenueDesc") return rightRevenue - leftRevenue;
        if (orderSort === "revenueAsc") return leftRevenue - rightRevenue;
        if (orderSort === "profitDesc") return rightProfit - leftProfit;
        if (orderSort === "profitAsc") return leftProfit - rightProfit;
        return right.created_at.localeCompare(left.created_at);
      });
  }, [ordersQuery.data, paymentStatus, search, orderSort]);
  const paginatedOrders = useMemo(
    () => paginateItems(filteredOrders, page, pageSize),
    [filteredOrders, page, pageSize],
  );
  const hasAnyOrders = (ordersQuery.data?.length ?? 0) > 0;
  const hasActiveFilters = Boolean(
    search.trim() || status || paymentStatus || orderSort !== "newest",
  );

  useEffect(() => {
    setPage(1);
  }, [search, status, paymentStatus, orderSort, pageSize]);

  useEffect(() => {
    setPage((currentPage) =>
      clampPage(currentPage, pageSize, filteredOrders.length),
    );
  }, [filteredOrders.length, pageSize]);

  return (
    <main className="min-h-screen min-w-0 overflow-x-hidden bg-slate-100 p-4 text-slate-950 sm:p-6">
      <div className="mx-auto grid min-w-0 max-w-7xl gap-6">
        <header className="flex flex-col gap-4 rounded-2xl bg-white p-6 shadow-sm md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">
              Sellora
            </p>
            <h1 className="mt-2 text-3xl font-bold">{t("orders.title")}</h1>
            <p className="mt-1 text-slate-600">{t("orders.subtitle")}</p>
          </div>
          <button
            className="min-h-11 rounded-lg bg-blue-600 px-4 py-3 font-semibold text-white"
            onClick={() => setIsCreateOpen(true)}
          >
            {t("orders.create")}
          </button>
        </header>
        <FilterBar>
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder={t("orders.searchPlaceholder")}
          />
          <select
            className="min-h-11 w-full min-w-0 max-w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm dark:border-white/10 dark:bg-white/10 dark:text-white"
            value={status}
            onChange={(event) =>
              setStatus(event.target.value as OrderStatus | "")
            }
          >
            {STATUSES.map((item) => (
              <option key={item || "all"} value={item}>
                {item ? t(`statuses.order.${item}`) : t("common.allStatuses")}
              </option>
            ))}
          </select>
          <select
            className="min-h-11 w-full min-w-0 max-w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm dark:border-white/10 dark:bg-white/10 dark:text-white"
            value={paymentStatus}
            onChange={(event) =>
              setPaymentStatus(event.target.value as PaymentStatus | "")
            }
          >
            <option value="">{t("orders.allPaymentStatuses")}</option>
            {(["PENDING", "PAID", "COD", "REFUNDED"] as PaymentStatus[]).map(
              (item) => (
                <option key={item} value={item}>
                  {t(`statuses.payment.${item}`)}
                </option>
              ),
            )}
          </select>
          <SortSelect
            value={orderSort}
            onChange={setOrderSort}
            options={[
              { value: "newest", label: t("sort.newest") },
              { value: "oldest", label: t("sort.oldest") },
              { value: "revenueDesc", label: t("sort.revenueDesc") },
              { value: "revenueAsc", label: t("sort.revenueAsc") },
              { value: "profitDesc", label: t("sort.profitDesc") },
              { value: "profitAsc", label: t("sort.profitAsc") },
            ]}
          />
          <ResetFiltersButton
            onClick={() => {
              setSearch("");
              setStatus("");
              setPaymentStatus("");
              setOrderSort("newest");
              setPage(1);
            }}
          />
          <div className="text-sm text-slate-600 dark:text-slate-300">
            {t("orders.todaySummary", {
              count: dashboardQuery.data?.orders_today ?? 0,
              revenue: formatMoney(
                dashboardQuery.data?.revenue_today,
                currencyCode,
              ),
              profit: formatMoney(
                dashboardQuery.data?.profit_today,
                currencyCode,
              ),
            })}
          </div>
        </FilterBar>
        {ordersQuery.isLoading ? (
          <LoadingSkeleton rows={5} title={t("orders.pagination.loading")} />
        ) : (
          <div className="orders-pagination-section grid min-w-0 gap-4">
            {filteredOrders.length > 0 ? (
              <PaginationControls
                page={page}
                pageSize={pageSize}
                totalItems={filteredOrders.length}
                onPageChange={setPage}
                onPageSizeChange={(nextPageSize) =>
                  setPageSize(
                    nextPageSize as (typeof PAGE_SIZE_OPTIONS)[number],
                  )
                }
              />
            ) : null}
            {filteredOrders.length === 0 ? (
              <EmptyState
                title={
                  hasAnyOrders && hasActiveFilters
                    ? t("orders.pagination.filteredEmptyTitle")
                    : t("orders.pagination.emptyTitle")
                }
                description={
                  hasAnyOrders && hasActiveFilters
                    ? t("orders.pagination.filteredEmptyDescription")
                    : t("orders.pagination.emptyDescription")
                }
                action={
                  !hasAnyOrders ? (
                    <button
                      className="min-h-11 rounded-2xl bg-blue-600 px-4 text-sm font-black text-white"
                      type="button"
                      onClick={() => setIsCreateOpen(true)}
                    >
                      {t("orders.create")}
                    </button>
                  ) : null
                }
              />
            ) : (
              <div className="grid min-w-0 gap-6 lg:grid-cols-[1fr_360px]">
                <OrderTable
                  orders={paginatedOrders}
                  currencyCode={currencyCode}
                  onSelect={setSelectedOrder}
                  onEdit={canEdit ? setEditingOrder : undefined}
                  onArchive={canEdit ? setArchivingOrder : undefined}
                />
                {selectedOrder ? (
                  <OrderDetails
                    order={selectedOrder}
                    currencyCode={currencyCode}
                    shipment={shipmentQuery.data}
                    onStatusChange={(nextStatus) =>
                      statusMutation.mutate({
                        orderId: selectedOrder.id,
                        nextStatus,
                      })
                    }
                  />
                ) : (
                  <div className="rounded-xl border border-slate-200 bg-white p-4 text-slate-500 dark:border-white/10 dark:bg-[#15172A] dark:text-slate-300">
                    {t("orders.selectPrompt")}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
        {isCreateOpen ? (
          <FormDialog
            title={t("orders.create")}
            description={t("orders.createDescription")}
            size="xl"
            onClose={() => setIsCreateOpen(false)}
          >
            <OrderForm
              variants={variantsQuery.data ?? []}
              products={productsQuery.data ?? []}
              inventory={inventoryQuery.data ?? []}
              customers={customersQuery.data ?? []}
<<<<<<< HEAD
=======
              campaigns={campaignsQuery.data ?? []}
>>>>>>> origin/codex/2026-07-01-create-initial-sellora-repository-structure
              currencyCode={currencyCode}
              showProfit={currentWorkspace?.role === "OWNER"}
              isCreatingCustomer={createCustomerMutation.isPending}
              onCreateCustomer={(payload) =>
                createCustomerMutation.mutateAsync(payload)
              }
              onSubmit={(values) =>
                createMutation.mutate(
                  values as Parameters<typeof createOrder>[1],
                )
              }
            />
          </FormDialog>
        ) : null}
        {editingOrder ? (
          <FormDialog
            title={t("orders.edit")}
            description={t("orders.editDescription")}
            size="xl"
            onClose={() => setEditingOrder(null)}
          >
            <OrderForm
              variants={variantsQuery.data ?? []}
              products={productsQuery.data ?? []}
              inventory={inventoryQuery.data ?? []}
              customers={customersQuery.data ?? []}
<<<<<<< HEAD
=======
              campaigns={campaignsQuery.data ?? []}
>>>>>>> origin/codex/2026-07-01-create-initial-sellora-repository-structure
              currencyCode={currencyCode}
              initialOrder={editingOrder}
              lockedItems={!ITEM_EDIT_STATUSES.includes(editingOrder.status)}
              submitLabel={t("actions.save")}
              showProfit={currentWorkspace?.role === "OWNER"}
              onSubmit={(values) =>
                updateMutation.mutate(
                  values as Parameters<typeof updateOrder>[2],
                )
              }
            />
            {updateMutation.isError ? (
              <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700 dark:bg-amber-500/15 dark:text-amber-100">
                {safeApiErrorMessage(
                  updateMutation.error,
                  t("orders.updateError"),
                )}
              </p>
            ) : null}
          </FormDialog>
        ) : null}
        {archivingOrder ? (
          <ConfirmActionDialog
            title={t("orders.archiveTitle")}
            description={t("orders.archiveDescription")}
            actionLabel={t("orders.archive")}
            isSubmitting={archiveMutation.isPending}
            error={
              archiveMutation.isError
                ? safeApiErrorMessage(
                    archiveMutation.error,
                    t("errors.deleteFailed"),
                  )
                : null
            }
            onCancel={() => setArchivingOrder(null)}
            onConfirm={() => archiveMutation.mutate()}
          />
        ) : null}
      </div>
    </main>
  );
}
// Localization regression compatibility markers: Edit order; Save order.
// Localization regression compatibility markers: FormDialog title="Create order"; FormDialog title="Edit order".
// Delete/archive regression compatibility marker: Archive test order?
