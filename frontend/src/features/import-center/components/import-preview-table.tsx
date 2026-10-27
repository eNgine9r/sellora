"use client";

import { ResponsiveReportTable } from "@/components/ui/responsive-report-table";
import { useI18n } from "@/i18n/provider";
import type { ImportPreview } from "@/types/import-center";

export function ImportPreviewTable({ preview }: { preview?: ImportPreview }) {
  const { t } = useI18n();
  if (!preview) return null;
  const columns = preview.columns.map((column) => ({
    key: column,
    label: column,
    render: (row: (typeof preview.rows)[number]) => String(row[column] ?? ""),
  }));
  return <section className="w-full min-w-0 rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm" data-import-preview>
    <h2 className="mb-3 font-semibold text-text-primary">{t("actions.preview")}</h2>
    <ResponsiveReportTable rows={preview.rows} columns={columns} rowKey={(_, index) => index} wide />
  </section>;
}
