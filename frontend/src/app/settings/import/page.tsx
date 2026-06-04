"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ColumnMappingForm } from "@/features/import-center/components/column-mapping-form";
import { ImportReportPanel } from "@/features/import-center/components/import-report-panel";
import { ImportLogsTable } from "@/features/import-center/components/import-logs-table";
import { ImportPreviewTable } from "@/features/import-center/components/import-preview-table";
import { ImportSummaryCard } from "@/features/import-center/components/import-summary-card";
import { ImportUploadCard } from "@/features/import-center/components/import-upload-card";
import { SheetSelector } from "@/features/import-center/components/sheet-selector";
import { ValidationReport } from "@/features/import-center/components/validation-report";
import { ValidationIssuesTable } from "@/features/import-center/components/validation-issues-table";
import { dryRunImport, executeImport, fetchImportLogs, fetchImportSheets, previewImportSheet, suggestImportMapping, uploadImportFile, validateImportMapping } from "@/services/import-center";
import { ImportJob, ImportPreview, ImportReport, MappingSuggestion, ValidationReport as ValidationReportType } from "@/types/import-center";
import { useAuth } from "@/hooks/use-auth";

const entityTypes = ["customers", "products", "product_variants", "inventory", "orders", "ad_campaigns", "ad_metrics", "product_catalog"];
const presets = [{ value: "your_jewelry_excel_v1", label: "your_jewelry_excel_v1" }, { value: "your_jewelry_product_catalog_v1", label: "your_jewelry_product_catalog_v1" }];

export default function ImportCenterPage() {
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const enabled = authStatus === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);
  const [jobId, setJobId] = useState("");
  const [job, setJob] = useState<ImportJob | null>(null);
  const [sheetName, setSheetName] = useState("");
  const [entityType, setEntityType] = useState("customers");
  const [preset, setPreset] = useState(presets[0].value);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<ImportPreview | undefined>();
  const [report, setReport] = useState<ValidationReportType | undefined>();
  const [dryRunReport, setDryRunReport] = useState<ImportReport | undefined>();
  const [suggestion, setSuggestion] = useState<MappingSuggestion | undefined>();
  const sheets = useQuery({ queryKey: ["import-sheets", workspaceId, jobId], queryFn: () => fetchImportSheets(workspaceId, jobId, undefined), enabled: enabled && Boolean(jobId) });
  const logs = useQuery({ queryKey: ["import-logs", workspaceId, jobId], queryFn: () => fetchImportLogs(workspaceId, jobId, undefined), enabled: enabled && Boolean(jobId) });
  const upload = useMutation({ mutationFn: (file: File) => uploadImportFile(workspaceId, file, undefined), onSuccess: (response) => setJobId(response.job_id) });
  function choosePreset(value: string) { setPreset(value); if (value === "your_jewelry_product_catalog_v1") { setEntityType("product_catalog"); setMapping({}); } }
  const previewMutation = useMutation({ mutationFn: () => previewImportSheet(workspaceId, jobId, sheetName, 20, undefined), onSuccess: setPreview });
  const suggestMutation = useMutation({ mutationFn: () => suggestImportMapping(workspaceId, jobId, sheetName, entityType, undefined), onSuccess: (response) => { setSuggestion(response); setMapping(response.suggested_mapping); } });
  const validateMutation = useMutation({ mutationFn: () => validateImportMapping(workspaceId, jobId, entityType, sheetName, mapping, undefined), onSuccess: setReport });
  const dryRunMutation = useMutation({ mutationFn: () => dryRunImport(workspaceId, jobId, entityType, sheetName, mapping, undefined), onSuccess: setDryRunReport });
  const executeMutation = useMutation({ mutationFn: () => executeImport(workspaceId, jobId, entityType, sheetName, mapping, undefined), onSuccess: (response) => { setJob(response.job); queryClient.invalidateQueries({ queryKey: ["import-logs", workspaceId, jobId] }); } });
  return <main className="min-h-screen bg-[#F8F7FC] p-4 sm:p-6 text-slate-950"><div className="mx-auto grid max-w-6xl gap-6"><header className="rounded-2xl bg-white p-6 shadow-sm"><p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Sellora Settings</p><h1 className="mt-2 text-3xl font-bold">Import Center</h1><p className="mt-1 text-slate-600">Upload, preview, validate, and import historical Excel data safely.</p></header><section className="rounded-xl bg-white p-4 shadow-sm"><label className="grid gap-2 text-sm font-semibold text-slate-700">Import preset<select className="min-h-11 rounded-lg border border-slate-300 px-3" value={preset} onChange={(event) => choosePreset(event.target.value)}>{presets.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>{preset === "your_jewelry_product_catalog_v1" ? <div className="mt-3 rounded-lg bg-blue-50 p-3 text-sm text-blue-800"><p className="font-bold">Product catalog import</p><p>This import creates Products, Variants, Inventory and Images from the product catalog template. It does not overwrite existing records.</p><p className="mt-2">Inventory can be derived from availability when quantity is empty or zero. Review dry-run warnings before importing.</p></div> : null}</section><ImportUploadCard onUpload={(file) => upload.mutate(file)} /><ImportSummaryCard job={job} />{jobId ? <section className="rounded-xl bg-white p-4 shadow-sm"><p className="text-sm text-slate-500">Import Job</p><p className="font-mono text-sm">{jobId}</p></section> : null}<section className="grid gap-3 rounded-xl bg-white p-4 shadow-sm md:grid-cols-3"><SheetSelector sheets={sheets.data?.sheets ?? []} value={sheetName} onChange={setSheetName} /><select className="rounded-md border border-slate-300 px-3 py-2" value={entityType} onChange={(event) => { setEntityType(event.target.value); setMapping({}); }}>{entityTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select><button className="rounded bg-blue-600 px-4 py-2 font-semibold text-white" onClick={() => previewMutation.mutate()} disabled={!sheetName}>Preview</button><button className="rounded bg-indigo-600 px-4 py-2 font-semibold text-white" onClick={() => suggestMutation.mutate()} disabled={!sheetName}>Suggest mapping</button></section><ImportPreviewTable preview={preview} />{preview ? <ColumnMappingForm entityType={entityType} columns={preview.columns} mapping={mapping} onChange={setMapping} /> : null}<section className="flex flex-wrap gap-3"><button className="rounded bg-emerald-600 px-4 py-2 font-semibold text-white" onClick={() => validateMutation.mutate()} disabled={!preview}>Validate</button><button className="rounded bg-amber-600 px-4 py-2 font-semibold text-white" onClick={() => dryRunMutation.mutate()} disabled={!preview}>Dry run</button><button className="rounded bg-slate-900 px-4 py-2 font-semibold text-white" onClick={() => executeMutation.mutate()} disabled={!dryRunReport || dryRunReport.error_rows > 0}>Execute import</button></section>{suggestion ? <section className="rounded-xl bg-white p-4 text-sm shadow-sm"><h2 className="font-semibold">Suggested mapping</h2><p>{Object.keys(suggestion.suggested_mapping).length} fields mapped. Missing required: {suggestion.required_fields_missing.join(", ") || "none"}</p></section> : null}<ValidationReport report={report} /><ValidationIssuesTable issues={report?.issues ?? []} /><ImportReportPanel report={dryRunReport} /><ImportLogsTable logs={logs.data ?? []} /></div></main>;
}
