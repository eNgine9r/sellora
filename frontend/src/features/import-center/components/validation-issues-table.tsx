"use client";

import { ResponsiveReportTable, type ReportTableColumn } from "@/components/ui/responsive-report-table";
import { getImportCenterPilotCopy, localizeImportIssue } from "@/features/import-center/import-center-pilot-copy";
import { useI18n } from "@/i18n/provider";
import type { ValidationIssue } from "@/types/import-center";

export function ValidationIssuesTable({ issues }: { issues: ValidationIssue[] }) {
  const { locale } = useI18n();
  const labels = getImportCenterPilotCopy(locale);
  if (!issues.length) return null;

  const columns: ReportTableColumn<ValidationIssue>[] = [
    { key: "row", label: labels.row, render: (issue) => issue.row_number ?? labels.mapping, emphasis: true },
    { key: "severity", label: labels.severity, render: (issue) => issue.severity === "WARNING" ? labels.warning : labels.error },
    { key: "field", label: labels.field, render: (issue) => issue.field || "—" },
    { key: "message", label: labels.message, render: (issue) => localizeImportIssue(issue, locale) },
  ];
  return <section className="w-full min-w-0 rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm" data-import-validation-issues>
    <h2 className="mb-3 font-semibold text-text-primary">{labels.validationTitle}</h2>
    <ResponsiveReportTable rows={issues} columns={columns} rowKey={(issue, index) => `${issue.row_number ?? "mapping"}-${issue.field ?? "general"}-${index}`} wide />
  </section>;
}
