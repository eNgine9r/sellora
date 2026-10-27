"use client";

import { ResponsiveReportTable, type ReportTableColumn } from "@/components/ui/responsive-report-table";
import { useI18n } from "@/i18n/provider";
import type { TopCustomer } from "@/types/analytics";

export function TopCustomersTable({ customers }: { customers: TopCustomer[] }) {
  const { t } = useI18n();
  const columns: ReportTableColumn<TopCustomer>[] = [
    { key: "customer", label: t("analytics.tables.customer"), render: (customer) => customer.name, emphasis: true },
    { key: "contact", label: t("analytics.tables.contact"), render: (customer) => customer.phone },
    { key: "orders", label: t("analytics.tables.orders"), render: (customer) => customer.total_orders },
    { key: "spent", label: t("analytics.tables.totalSpent"), render: (customer) => customer.total_spent },
  ];
  return <section className="min-w-0 rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm">
    <h3 className="mb-3 font-semibold text-text-primary">{t("analytics.customers.title")}</h3>
    <ResponsiveReportTable rows={customers} columns={columns} rowKey={(customer) => customer.customer_id} />
  </section>;
}
