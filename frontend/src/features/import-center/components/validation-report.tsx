"use client";

import { getImportCenterPilotCopy, localizeImportIssue } from "@/features/import-center/import-center-pilot-copy";
import { useI18n } from "@/i18n/provider";
import { ValidationReport as Report, ValidationIssue } from "@/types/import-center";

export function ValidationReport({ report }: { report?: Report }) {
  const { locale } = useI18n();
  const labels = getImportCenterPilotCopy(locale);
  if (!report) return null;

  const fallbackIssue = (message: string, severity: "ERROR" | "WARNING"): ValidationIssue => ({
    row_number: null,
    severity,
    field: null,
    message,
  });

  return (
    <section className="w-full min-w-0 max-w-full overflow-hidden rounded-xl bg-white p-4 shadow-sm" data-import-validation-report>
      <h2 className="font-semibold">{labels.validationReport}</h2>
      <p className={report.is_valid ? "break-words text-green-600" : "break-words text-red-600"}>
        {report.is_valid ? labels.valid : labels.invalid} · {report.total_rows} {labels.rows}
      </p>
      {report.errors.map((error, index) => <p className="break-words text-sm text-red-600" key={`error-${index}`}>{localizeImportIssue(fallbackIssue(error, "ERROR"), locale)}</p>)}
      {report.warnings.map((warning, index) => <p className="break-words text-sm text-amber-600" key={`warning-${index}`}>{localizeImportIssue(fallbackIssue(warning, "WARNING"), locale)}</p>)}
    </section>
  );
}
