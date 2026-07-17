"use client";

import { getImportCenterPilotCopy, localizeImportIssue } from "@/features/import-center/import-center-pilot-copy";
import { useI18n } from "@/i18n/provider";
import { ImportLog, ValidationIssue } from "@/types/import-center";

export function ImportLogsTable({ logs }: { logs: ImportLog[] }) {
  const { t, locale } = useI18n();
  const labels = getImportCenterPilotCopy(locale);

  return (
    <div className="w-full min-w-0 max-w-full overflow-hidden rounded-xl bg-white p-4 shadow-sm dark:bg-slate-900" data-import-logs>
      <h2 className="mb-3 font-semibold">{t("importCenter.logs")}</h2>
      <div className="sellora-scrollbar max-w-full overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="text-slate-500 dark:text-slate-400">
              <th>{t("tables.row")}</th>
              <th>{t("tables.status")}</th>
              <th>{t("tables.message")}</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => {
              const issue: ValidationIssue = {
                row_number: log.row_number,
                severity: log.status === "WARNING" || log.status === "SKIPPED" ? "WARNING" : log.status === "FAILED" ? "ERROR" : "WARNING",
                field: null,
                message: log.message || "",
              };
              const status = log.status === "FAILED"
                ? labels.error
                : log.status === "WARNING"
                  ? labels.warning
                  : log.status;
              return (
                <tr className="border-t border-slate-200 dark:border-slate-800" key={log.id}>
                  <td className="py-2">{log.row_number}</td>
                  <td>{status}</td>
                  <td className="break-words">{log.message ? localizeImportIssue(issue, locale) : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
