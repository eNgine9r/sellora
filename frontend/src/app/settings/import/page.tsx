"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ColumnMappingForm } from "@/features/import-center/components/column-mapping-form";
import { ImportLogsTable } from "@/features/import-center/components/import-logs-table";
import { ImportPreviewTable } from "@/features/import-center/components/import-preview-table";
import { ImportSummaryCard } from "@/features/import-center/components/import-summary-card";
import { ImportUploadCard } from "@/features/import-center/components/import-upload-card";
import { SheetSelector } from "@/features/import-center/components/sheet-selector";
import { ValidationReport } from "@/features/import-center/components/validation-report";
import { executeImport, fetchImportLogs, fetchImportSheets, previewImportSheet, uploadImportFile, validateImportMapping } from "@/services/import-center";
import { ImportJob, ImportPreview, ValidationReport as ValidationReportType } from "@/types/import-center";

const entityTypes = ["customers", "products", "product_variants", "inventory", "orders"];

export default function ImportCenterPage() {
  const queryClient = useQueryClient();
  const [workspaceId, setWorkspaceId] = useState("");
  const [token, setToken] = useState("");
  const [jobId, setJobId] = useState("");
  const [job, setJob] = useState<ImportJob | null>(null);
  const [sheetName, setSheetName] = useState("");
  const [entityType, setEntityType] = useState("customers");
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<ImportPreview | undefined>();
  const [report, setReport] = useState<ValidationReportType | undefined>();
  const sheets = useQuery({ queryKey: ["import-sheets", workspaceId, jobId], queryFn: () => fetchImportSheets(workspaceId, jobId, token), enabled: Boolean(workspaceId && jobId) });
  const logs = useQuery({ queryKey: ["import-logs", workspaceId, jobId], queryFn: () => fetchImportLogs(workspaceId, jobId, token), enabled: Boolean(workspaceId && jobId) });
  const upload = useMutation({ mutationFn: (file: File) => uploadImportFile(workspaceId, file, token), onSuccess: (response) => setJobId(response.job_id) });
  const previewMutation = useMutation({ mutationFn: () => previewImportSheet(workspaceId, jobId, sheetName, 20, token), onSuccess: setPreview });
  const validateMutation = useMutation({ mutationFn: () => validateImportMapping(workspaceId, jobId, entityType, sheetName, mapping, token), onSuccess: setReport });
  const executeMutation = useMutation({ mutationFn: () => executeImport(workspaceId, jobId, entityType, sheetName, mapping, token), onSuccess: (response) => { setJob(response.job); queryClient.invalidateQueries({ queryKey: ["import-logs", workspaceId, jobId] }); } });
  return <main className="min-h-screen bg-slate-100 p-6 text-slate-950"><div className="mx-auto grid max-w-6xl gap-6"><header className="rounded-2xl bg-white p-6 shadow-sm"><p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Sellora Settings</p><h1 className="mt-2 text-3xl font-bold">Import Center</h1><p className="mt-1 text-slate-600">Upload, preview, validate, and import historical Excel data safely.</p></header><section className="grid gap-3 rounded-2xl bg-white p-4 shadow-sm md:grid-cols-2"><input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Workspace ID" value={workspaceId} onChange={(event) => setWorkspaceId(event.target.value)} /><input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Owner access token" value={token} onChange={(event) => setToken(event.target.value)} /></section><ImportUploadCard onUpload={(file) => upload.mutate(file)} /><ImportSummaryCard job={job} />{jobId ? <section className="rounded-xl bg-white p-4 shadow-sm"><p className="text-sm text-slate-500">Import Job</p><p className="font-mono text-sm">{jobId}</p></section> : null}<section className="grid gap-3 rounded-xl bg-white p-4 shadow-sm md:grid-cols-3"><SheetSelector sheets={sheets.data?.sheets ?? []} value={sheetName} onChange={setSheetName} /><select className="rounded-md border border-slate-300 px-3 py-2" value={entityType} onChange={(event) => { setEntityType(event.target.value); setMapping({}); }}>{entityTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select><button className="rounded bg-blue-600 px-4 py-2 font-semibold text-white" onClick={() => previewMutation.mutate()} disabled={!sheetName}>Preview</button></section><ImportPreviewTable preview={preview} />{preview ? <ColumnMappingForm entityType={entityType} columns={preview.columns} mapping={mapping} onChange={setMapping} /> : null}<section className="flex gap-3"><button className="rounded bg-emerald-600 px-4 py-2 font-semibold text-white" onClick={() => validateMutation.mutate()} disabled={!preview}>Validate</button><button className="rounded bg-slate-900 px-4 py-2 font-semibold text-white" onClick={() => executeMutation.mutate()} disabled={!report?.is_valid}>Execute import</button></section><ValidationReport report={report} /><ImportLogsTable logs={logs.data ?? []} /></div></main>;
}
