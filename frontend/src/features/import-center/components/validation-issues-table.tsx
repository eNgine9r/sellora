"use client";

import { getImportCenterPilotCopy, localizeImportIssue } from "@/features/import-center/import-center-pilot-copy";
import { useI18n } from "@/i18n/provider";
import { ValidationIssue } from "@/types/import-center";

export function ValidationIssuesTable({ issues }: { issues: ValidationIssue[] }) {
  const { locale } = useI18n();
  const labels = getImportCenterPilotCopy(locale);
  if (!issues.length) return null;

  return (
    <div
      className="w-full min-w-0 max-w-full overflow-hidden rounded-xl bg-white p-4 shadow-sm dark:bg-slate-900"
      data-import-validation-issues
    >
      <h2 className="mb-3 font-semibold">{labels.validationTitle}</h2>
      <div className="sellora-scrollbar max-w-full overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="text-slate-500 dark:text-slate-400">
              <th>{labels.row}</th>
              <th>{labels.severity}</th>
              <th>{labels.field}</th>
              <th>{labels.message}</th>
            </tr>
          </thead>
          <tbody>
            {issues.map((issue, index) => (
              <tr className="border-t border-slate-200 dark:border-slate-800" key={`${issue.row_number ?? "mapping"}-${issue.field ?? "general"}-${index}`}>
                <td className="py-2">{issue.row_number ?? labels.mapping}</td>
                <td>{issue.severity === "WARNING" ? labels.warning : labels.error}</td>
                <td>{issue.field || "—"}</td>
                <td className="break-words">{localizeImportIssue(issue, locale)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
