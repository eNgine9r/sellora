"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { WorkspacePage, WorkspaceHeader } from "@/components/crm-workspace";
import { Card } from "@/components/ui/primitives";
import { useEffect, useMemo, useState } from "react";
import { ColumnMappingForm } from "@/features/import-center/components/column-mapping-form";
import { ImportReportPanel } from "@/features/import-center/components/import-report-panel";
import { ImportPilotHelp } from "@/components/pilot-readiness";
import { ImportLogsTable } from "@/features/import-center/components/import-logs-table";
import { ImportPreviewTable } from "@/features/import-center/components/import-preview-table";
import { ImportSummaryCard } from "@/features/import-center/components/import-summary-card";
import { ImportUploadCard } from "@/features/import-center/components/import-upload-card";
import { SheetSelector } from "@/features/import-center/components/sheet-selector";
import { ValidationReport } from "@/features/import-center/components/validation-report";
import { ValidationIssuesTable } from "@/features/import-center/components/validation-issues-table";
import { getImportCenterPilotCopy } from "@/features/import-center/import-center-pilot-copy";
import { dryRunImport, executeImport, fetchImportLogs, fetchImportSheets, previewImportSheet, suggestImportMapping, uploadImportFile, validateImportMapping } from "@/services/import-center";
import { ImportJob, ImportPreview, ImportReport, MappingSuggestion, ValidationReport as ValidationReportType } from "@/types/import-center";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";

const entityTypes = ["customers", "products", "product_variants", "inventory", "orders", "ad_campaigns", "ad_metrics", "product_catalog", "orders_history", "advertising_history"];
const presets = [
  { value: "your_jewelry_excel_v1", labelKey: "importCenter.title" },
  { value: "your_jewelry_product_catalog_v1", labelKey: "importCenter.productCatalog" },
  { value: "your_jewelry_orders_history_v1", labelKey: "importCenter.ordersHistory" },
  { value: "your_jewelry_advertising_history_v1", labelKey: "importCenter.advertisingHistory" },
];

export default function ImportCenterPage() {
  const { t, locale } = useI18n();
  const pilotCopy = getImportCenterPilotCopy(locale);
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
  const [affectInventory, setAffectInventory] = useState(false);
  const dryRunKey = useMemo(() => JSON.stringify({ workspaceId, jobId, entityType, sheetName, mapping, importOptions: entityType === "orders_history" ? { affect_inventory: affectInventory } : undefined }), [workspaceId, jobId, entityType, sheetName, mapping, affectInventory]);
  const [approvedDryRunKey, setApprovedDryRunKey] = useState<string | null>(null);
  useEffect(() => {
    setJobId("");
    setJob(null);
    setSheetName("");
    setMapping({});
    setPreview(undefined);
    setReport(undefined);
    setDryRunReport(undefined);
    setSuggestion(undefined);
    setApprovedDryRunKey(null);
  }, [workspaceId]);
  const sheets = useQuery({ queryKey: ["import-sheets", workspaceId, jobId], queryFn: () => fetchImportSheets(workspaceId, jobId, undefined), enabled: enabled && Boolean(jobId) });
  const logs = useQuery({ queryKey: ["import-logs", workspaceId, jobId], queryFn: () => fetchImportLogs(workspaceId, jobId, undefined), enabled: enabled && Boolean(jobId) });
  const upload = useMutation({ mutationFn: (file: File) => uploadImportFile(workspaceId, file, undefined), onSuccess: (response) => { setJobId(response.job_id); setSheetName(""); setMapping({}); setPreview(undefined); setReport(undefined); setDryRunReport(undefined); setApprovedDryRunKey(null); } });
  function choosePreset(value: string) { setPreset(value); setDryRunReport(undefined); setApprovedDryRunKey(null); if (value === "your_jewelry_product_catalog_v1") { setEntityType("product_catalog"); setMapping({}); } else if (value === "your_jewelry_orders_history_v1") { setEntityType("orders_history"); setMapping({}); setAffectInventory(false); } else if (value === "your_jewelry_advertising_history_v1") { setEntityType("advertising_history"); setMapping({}); } }
  const importOptions = entityType === "orders_history" ? { affect_inventory: affectInventory } : undefined;
  const previewMutation = useMutation({ mutationFn: () => previewImportSheet(workspaceId, jobId, sheetName, 20, undefined), onSuccess: setPreview });
  const suggestMutation = useMutation({ mutationFn: () => suggestImportMapping(workspaceId, jobId, sheetName, entityType, undefined), onSuccess: (response) => { setSuggestion(response); setMapping(response.suggested_mapping); } });
  const validateMutation = useMutation({ mutationFn: () => validateImportMapping(workspaceId, jobId, entityType, sheetName, mapping, undefined, importOptions), onSuccess: setReport });
  const dryRunMutation = useMutation({ mutationFn: () => dryRunImport(workspaceId, jobId, entityType, sheetName, mapping, undefined, importOptions), onSuccess: (response) => { setDryRunReport(response); setApprovedDryRunKey(dryRunKey); } });
  const executeMutation = useMutation({ mutationFn: () => executeImport(workspaceId, jobId, entityType, sheetName, mapping, undefined, importOptions), onSuccess: (response) => { setJob(response.job); queryClient.invalidateQueries({ queryKey: ["import-logs", workspaceId, jobId] }); } });
  return <WorkspacePage><WorkspaceHeader eyebrow={t("importCenter.settingsEyebrow")} title={t("importCenter.title")} description={t("importCenter.subtitle")} /><ImportPilotHelp /><Card className="min-w-0 max-w-full overflow-hidden"><label className="grid min-w-0 gap-2 text-sm font-semibold text-slate-700">{t("importCenter.preset")}<select className="min-h-11 w-full min-w-0 max-w-full truncate rounded-lg border border-slate-300 px-3" value={preset} onChange={(event) => choosePreset(event.target.value)}>{presets.map((item) => <option key={item.value} value={item.value}>{t(item.labelKey)}</option>)}</select></label>{preset === "your_jewelry_product_catalog_v1" ? <div className="mt-3 rounded-lg bg-blue-50 p-3 text-sm text-blue-800"><p className="font-bold">{t("importCenter.productCatalog")}</p><p>{t("importCenter.productCatalogHelp")}</p><p className="mt-2">{t("importHelp.productColumns")}</p></div> : null}{preset === "your_jewelry_orders_history_v1" ? <div className="mt-3 grid gap-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-900"><p className="font-bold">{t("importCenter.ordersHistory")}</p><p>{t("importCenter.ordersHistoryHelp")}</p><label className="flex items-center gap-2 font-semibold"><input type="checkbox" checked={affectInventory} onChange={(event) => { setAffectInventory(event.target.checked); setDryRunReport(undefined); setApprovedDryRunKey(null); }} /> {t("importCenter.affectInventory")}</label>{affectInventory ? <p className="rounded-lg bg-white p-2 text-red-700">{t("importCenter.affectInventoryWarning")}</p> : null}</div> : null}{preset === "your_jewelry_advertising_history_v1" ? <div className="mt-3 grid gap-2 rounded-lg bg-purple-50 p-3 text-sm text-purple-900"><p className="font-bold">{t("importCenter.templateTitle")}</p><p>{t("importCenter.advertisingHistoryHelp")}</p><p>{t("importCenter.templateHelp")}</p><p className="font-semibold">{t("importCenter.requiredColumns")}</p><p>{t("importCenter.optionalColumns")}</p><p>{t("importCenter.duplicateHint")}</p><div className="flex flex-wrap gap-2"><a className="rounded-lg bg-purple-700 px-3 py-2 font-bold text-white" href="/templates/advertising-import-template.csv" download>{t("importCenter.downloadTemplate")}</a><a className="rounded-lg border border-purple-200 bg-white px-3 py-2 font-bold text-purple-800" href="/advertising">{t("importCenter.afterImport")}</a></div></div> : null}</Card><ImportUploadCard onUpload={(file) => upload.mutate(file)} isUploading={upload.isPending} /><ImportSummaryCard job={job} />{jobId ? <section className="rounded-xl bg-white p-4 shadow-sm"><p className="text-sm text-slate-500">{t("importCenter.importJob")}</p><p className="font-mono text-sm">{jobId}</p></section> : null}<section className="grid min-w-0 max-w-full gap-3 overflow-hidden rounded-xl bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-4"><SheetSelector sheets={sheets.data?.sheets ?? []} value={sheetName} onChange={(value) => { setSheetName(value); setPreview(undefined); setReport(undefined); setDryRunReport(undefined); setApprovedDryRunKey(null); }} /><select className="w-full min-w-0 max-w-full truncate rounded-md border border-slate-300 px-3 py-2" value={entityType} onChange={(event) => { setEntityType(event.target.value); setMapping({}); setPreview(undefined); setReport(undefined); setDryRunReport(undefined); setApprovedDryRunKey(null); }}>{entityTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select><button className="min-h-11 w-full min-w-0 whitespace-normal rounded bg-blue-600 px-4 py-2 font-semibold text-white" onClick={() => previewMutation.mutate()} disabled={!sheetName}>{t("actions.preview")}</button><button className="min-h-11 w-full min-w-0 whitespace-normal rounded bg-indigo-600 px-4 py-2 font-semibold text-white" onClick={() => suggestMutation.mutate()} disabled={!sheetName}>{t("importCenter.suggestMapping")}</button></section><ImportPreviewTable preview={preview} />{preview ? <ColumnMappingForm entityType={entityType} columns={preview.columns} mapping={mapping} onChange={(value) => { setMapping(value); setDryRunReport(undefined); setApprovedDryRunKey(null); }} /> : null}<section className="flex min-w-0 max-w-full flex-wrap gap-3 overflow-hidden"><button className="min-h-11 w-full min-w-0 whitespace-normal rounded bg-emerald-600 px-4 py-2 font-semibold text-white sm:w-auto" onClick={() => validateMutation.mutate()} disabled={!preview}>{t("importCenter.validate")}</button><button className="min-h-11 w-full min-w-0 whitespace-normal rounded bg-amber-600 px-4 py-2 font-semibold text-white sm:w-auto" onClick={() => dryRunMutation.mutate()} disabled={!preview}>{t("importCenter.dryRun")}</button><button className="min-h-11 w-full min-w-0 whitespace-normal rounded bg-slate-900 px-4 py-2 font-semibold text-white sm:w-auto" onClick={() => executeMutation.mutate()} disabled={!dryRunReport || dryRunReport.error_rows > 0 || approvedDryRunKey !== dryRunKey || executeMutation.isPending}>{t("importCenter.executeImport")}</button></section>{suggestion ? <section className="rounded-xl bg-white p-4 text-sm shadow-sm"><h2 className="font-semibold">{t("importCenter.suggestedMapping")}</h2><p>{Object.keys(suggestion.suggested_mapping).length} {t("importCenter.fieldsMapped")}. {t("importCenter.missingRequired")}: {suggestion.required_fields_missing.join(", ") || t("common.none")}</p></section> : null}<ValidationReport report={report} /><ValidationIssuesTable issues={report?.issues ?? []} /><ImportReportPanel report={dryRunReport} />{dryRunReport && dryRunReport.error_rows === 0 ? <section className="rounded-xl bg-emerald-50 p-4 text-sm text-emerald-900 shadow-sm"><p className="font-bold">{t("importHelp.successNextTitle")}</p><p>{t("importHelp.successNextDescription")}</p></section> : null}<ImportLogsTable logs={logs.data ?? []} /></WorkspacePage>;
}

// Localization regression compatibility markers: affect_inventory; It does not affect current inventory by default.; It does not connect to Meta Ads API.
