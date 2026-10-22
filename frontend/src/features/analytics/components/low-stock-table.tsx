"use client";

import { ResponsiveReportTable, type ReportTableColumn } from "@/components/ui/responsive-report-table";
import { useI18n } from "@/i18n/provider";
import type { LowStockItem } from "@/types/analytics";

export function LowStockTable({ items }: { items: LowStockItem[] }) {
  const { t } = useI18n();
  const columns: ReportTableColumn<LowStockItem>[] = [
    { key: "product", label: t("analytics.tables.product"), render: (item) => item.product_name, emphasis: true },
    { key: "sku", label: t("analytics.tables.sku"), render: (item) => item.variant_sku },
    { key: "stock", label: t("analytics.tables.stock"), render: (item) => item.stock_quantity },
    { key: "reserved", label: t("analytics.tables.reserved"), render: (item) => item.reserved_quantity },
    { key: "minimum", label: t("analytics.tables.minimum"), render: (item) => item.minimum_quantity },
  ];
  return <section className="min-w-0 rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm">
    <h3 className="mb-3 font-semibold text-text-primary">{t("analytics.inventory.title")}</h3>
    <ResponsiveReportTable rows={items} columns={columns} rowKey={(item) => item.variant_id} />
  </section>;
}
