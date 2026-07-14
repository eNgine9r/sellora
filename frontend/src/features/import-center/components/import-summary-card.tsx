"use client";

import { ImportJob } from "@/types/import-center";
import { ImportJobStatusBadge } from "@/features/import-center/components/import-job-status-badge";
import { getImportCenterPilotCopy } from "@/features/import-center/import-center-pilot-copy";
import { useI18n } from "@/i18n/provider";

export function ImportSummaryCard({ job }: { job?: ImportJob | null }) {
  const { locale } = useI18n();
  const labels = getImportCenterPilotCopy(locale);
  if (!job) return null;
  return (
    <section className="w-full min-w-0 max-w-full overflow-hidden rounded-xl bg-white p-4 shadow-sm" data-import-job-summary>
      <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="min-w-0 truncate font-semibold" title={job.file_name}>{job.file_name}</h2>
        <ImportJobStatusBadge status={job.status} />
      </div>
      <div className="mt-3 grid min-w-0 gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <span>{labels.total}: {job.total_rows}</span>
        <span>{labels.processed}: {job.processed_rows}</span>
        <span>{labels.success}: {job.success_rows}</span>
        <span>{labels.failed}: {job.failed_rows}</span>
      </div>
    </section>
  );
}
