export type ImportJobStatus = "UPLOADED" | "PREVIEWED" | "VALIDATED" | "IMPORTING" | "COMPLETED" | "FAILED" | "PARTIALLY_COMPLETED" | "CANCELLED";
export type ImportJob = { id: string; workspace_id: string; file_name: string; file_type: string; status: ImportJobStatus; total_rows: number; processed_rows: number; success_rows: number; failed_rows: number; created_at: string; updated_at: string; completed_at?: string | null };
export type ImportLog = { id: string; row_number?: number | null; entity_type: string; status: "SUCCESS" | "FAILED" | "SKIPPED" | "WARNING"; message?: string | null; raw_data?: Record<string, unknown> | null; created_at: string };
export type ImportPreview = { columns: string[]; rows: Record<string, unknown>[] };
export type ValidationReport = { is_valid: boolean; total_rows: number; errors: string[]; warnings: string[] };
export type MappingPreset = { name: string; sheets: string[]; mappings: Record<string, Record<string, string>> };
