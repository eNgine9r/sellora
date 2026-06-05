import { ImportJobStatus } from "@/types/import-center";
export function ImportJobStatusBadge({ status }: { status?: ImportJobStatus | string }) { if (!status) return null; return <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700">{status}</span>; }
