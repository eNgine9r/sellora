"use client";

import { ResponsiveReportTable, type ReportTableColumn } from "@/components/ui/responsive-report-table";
import { getImportCenterPilotCopy, localizeImportIssue } from "@/features/import-center/import-center-pilot-copy";
import { useI18n } from "@/i18n/provider";
import type { ImportLog, ValidationIssue } from "@/types/import-center";

export function ImportLogsTable({ logs }: { logs: ImportLog[] }) {
  const { t, locale } = useI18n();
  const labels = getImportCenterPilotCopy(locale);
  const columns: ReportTableColumn<ImportLog>[] = [
    { key: "row", label: t("tables.row"), render: (log) => log.row_number, emphasis: true },
    { key: "status", label: t("tables.status"), render: (log) => log.status === "FAILED" ? labels.error : log.status === "WARNING" ? labels.warning : log.status },
    { key: "message", label: t("tables.message"), render: (log) => {
      const issue: ValidationIssue = {
        row_number: log.row_number,
        severity: log.status === "FAILED" ? "ERROR" : "WARNING",
        field: null,
        message: log.message || "",
      };
      return log.message ? localizeImportIssue(issue, locale) : "—";
    } },
  ];
  return <section className="w-full min-w-0 rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm" data-import-logs>
    <h2 className="mb-3 font-semibold text-text-primary">{t("importCenter.logs")}</h2>
    <ResponsiveReportTable rows={logs} columns={columns} rowKey={(log) => log.id} />
  </section>;
}
