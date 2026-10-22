"use client";

import { ResponsiveReportTable, type ReportTableColumn } from "@/components/ui/responsive-report-table";
import { useI18n } from "@/i18n/provider";
import type { TopProduct } from "@/types/analytics";

export function TopProductsTable({ products, showProfit = false }: { products: TopProduct[]; showProfit?: boolean }) {
  const { t } = useI18n();
  const columns: ReportTableColumn<TopProduct>[] = [
    { key: "product", label: t("analytics.tables.product"), render: (item) => item.product_name, emphasis: true },
    { key: "sku", label: t("analytics.tables.sku"), render: (item) => item.variant_sku },
    { key: "quantity", label: t("analytics.tables.quantitySold"), render: (item) => item.quantity_sold },
    { key: "revenue", label: t("analytics.tables.revenue"), render: (item) => item.revenue },
    ...(showProfit ? [{ key: "profit", label: t("analytics.tables.netProfit"), render: (item: TopProduct) => item.net_profit }] : []),
  ];
  return <section className="min-w-0 rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm">
    <h3 className="mb-3 font-semibold text-text-primary">{t("analytics.products.title")}</h3>
    <ResponsiveReportTable rows={products} columns={columns} rowKey={(item) => item.variant_id} />
  </section>;
}
