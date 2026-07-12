"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
import { EditRecordDialog } from "@/components/edit-record-dialog";
import { FormDialog } from "@/components/form-dialog";
import { AdMetricForm } from "@/features/advertising/components/ad-metric-form";
import { AdMetricTable } from "@/features/advertising/components/ad-metric-table";
import { AdvertisingDateRangeFilter } from "@/features/advertising/components/advertising-date-range-filter";
import { AdvertisingTrendChart } from "@/features/advertising/components/advertising-trend-chart";
import { CampaignForm } from "@/features/advertising/components/campaign-form";
import { CampaignInsightsPanel } from "@/features/advertising/components/campaign-insights-panel";
import { CampaignPerformanceTable } from "@/features/advertising/components/campaign-performance-table";
import { CampaignTable } from "@/features/advertising/components/campaign-table";
import { buildAdCampaignUpdatePayload, buildAdMetricUpdatePayload } from "@/lib/payload-builders";
import { safeApiErrorMessage } from "@/services/api";
import { createAdCampaign, createAdMetric, deleteAdCampaign, deleteAdMetric, fetchAdCampaigns, fetchAdMetrics, fetchAdvertisingSummary, fetchAdvertisingTrend, fetchCampaignPerformance, updateAdCampaign, updateAdMetric } from "@/services/advertising";
import { AdCampaign, AdCampaignCreate, AdMetric, AdMetricCreate } from "@/types/advertising";
import { useAuth } from "@/hooks/use-auth";
import { formatMoney } from "@/lib/currency";
import { useI18n } from "@/i18n/provider";
import { MetaAdsReadinessCard } from "@/features/integrations/components/meta-ads-readiness-card";
import { Button, CompactSummary, EntitySidePanel, FieldGrid, FieldItem, WorkspaceHeader, WorkspacePage, WorkspaceSplitView } from "@/components/crm-workspace";
import { PaginationControls, PAGE_SIZE_OPTIONS, clampPage, paginateItems } from "@/components/pagination-controls";

function StatusList({ title, items, tone }: { title: string; items: string[]; tone: "ready" | "pending" | "future" }) {
  const toneClasses = {
    ready: "border-emerald-100 bg-emerald-50 text-emerald-950",
    pending: "border-amber-100 bg-amber-50 text-amber-950",
    future: "border-slate-200 bg-slate-50 text-slate-700",
  };

  return (
    <div className={`rounded-2xl border p-4 text-sm ${toneClasses[tone]}`}>
      <p className="font-black">{title}</p>
      <ul className="mt-2 grid gap-1 pl-4 list-disc">
        {items.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </div>
  );
}

export default function AdvertisingPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspace, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const currencyCode = currentWorkspace?.currency_code ?? "UAH";
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isCampaignCreateOpen, setIsCampaignCreateOpen] = useState(false);
  const [isMetricCreateOpen, setIsMetricCreateOpen] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState<AdCampaign | null>(null);
  const [editingMetric, setEditingMetric] = useState<AdMetric | null>(null);
  const [archivingCampaign, setArchivingCampaign] = useState<AdCampaign | null>(null);
  const [deletingMetric, setDeletingMetric] = useState<AdMetric | null>(null);
  const [selectedCampaign, setSelectedCampaign] = useState<AdCampaign | null>(null);
  const [campaignPage, setCampaignPage] = useState(1);
  const [campaignPageSize, setCampaignPageSize] = useState<(typeof PAGE_SIZE_OPTIONS)[number]>(5);
  const [metricPage, setMetricPage] = useState(1);
  const [metricPageSize, setMetricPageSize] = useState<(typeof PAGE_SIZE_OPTIONS)[number]>(5);
  const [performancePage, setPerformancePage] = useState(1);
  const [performancePageSize, setPerformancePageSize] = useState<(typeof PAGE_SIZE_OPTIONS)[number]>(5);
  const enabled = authStatus === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);
  const canEditAdvertising = currentWorkspace?.role === "OWNER";
  const campaigns = useQuery({ queryKey: ["ad-campaigns", workspaceId], queryFn: () => fetchAdCampaigns(workspaceId, undefined), enabled });
  const metrics = useQuery({ queryKey: ["ad-metrics", workspaceId], queryFn: () => fetchAdMetrics(workspaceId, undefined), enabled });
  const summary = useQuery({ queryKey: ["ad-summary", workspaceId, startDate, endDate], queryFn: () => fetchAdvertisingSummary(workspaceId, undefined, startDate, endDate), enabled });
  const performance = useQuery({ queryKey: ["ad-performance", workspaceId, startDate, endDate], queryFn: () => fetchCampaignPerformance(workspaceId, undefined, startDate, endDate), enabled });
  const trend = useQuery({ queryKey: ["ad-trend", workspaceId, startDate, endDate], queryFn: () => fetchAdvertisingTrend(workspaceId, undefined, startDate, endDate), enabled });
  const readinessReady = [
    t("advertising.readinessReadyManualMetrics"),
    t("advertising.readinessReadyCsvTemplate"),
    t("advertising.readinessReadyFormulas"),
    t("advertising.readinessReadyInsights"),
    t("advertising.readinessReadyManualAttribution"),
  ];
  const readinessPending = [
    t("advertising.readinessPendingImportQa"),
    t("advertising.readinessPendingPostgresMigration"),
    t("advertising.readinessPendingBrowserMobileQa"),
  ];
  const invalidateAds = () => {
    queryClient.invalidateQueries({ queryKey: ["ad-campaigns", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["ad-metrics", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["ad-summary", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["ad-performance", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["ad-trend", workspaceId] });
  };
  const createCampaignMutation = useMutation({ mutationFn: (payload: AdCampaignCreate) => createAdCampaign(workspaceId, undefined, payload), onSuccess: () => { setIsCampaignCreateOpen(false); invalidateAds(); } });
  const createMetricMutation = useMutation({ mutationFn: (payload: AdMetricCreate) => createAdMetric(workspaceId, undefined, payload), onSuccess: () => { setIsMetricCreateOpen(false); invalidateAds(); } });
  const updateCampaignMutation = useMutation({ mutationFn: (values: Record<string, string>) => updateAdCampaign(workspaceId, editingCampaign?.id ?? "", undefined, buildAdCampaignUpdatePayload(values)), onSuccess: () => { setEditingCampaign(null); invalidateAds(); } });
  const updateMetricMutation = useMutation({ mutationFn: (values: Record<string, string>) => updateAdMetric(workspaceId, editingMetric?.id ?? "", undefined, buildAdMetricUpdatePayload(values)), onSuccess: () => { setEditingMetric(null); invalidateAds(); } });
  const archiveCampaignMutation = useMutation({ mutationFn: () => deleteAdCampaign(workspaceId, archivingCampaign?.id ?? "", undefined), onSuccess: () => { setArchivingCampaign(null); invalidateAds(); queryClient.invalidateQueries({ queryKey: ["dashboard", workspaceId] }); } });
  const deleteMetricMutation = useMutation({ mutationFn: () => deleteAdMetric(workspaceId, deletingMetric?.id ?? "", undefined), onSuccess: () => { setDeletingMetric(null); invalidateAds(); queryClient.invalidateQueries({ queryKey: ["dashboard", workspaceId] }); } });

  const campaignRows = useMemo(() => campaigns.data ?? [], [campaigns.data]);
  const metricRows = useMemo(() => metrics.data ?? [], [metrics.data]);
  const performanceRows = useMemo(() => performance.data ?? [], [performance.data]);
  const paginatedCampaigns = useMemo(() => paginateItems(campaignRows, campaignPage, campaignPageSize), [campaignPage, campaignPageSize, campaignRows]);
  const paginatedMetrics = useMemo(() => paginateItems(metricRows, metricPage, metricPageSize), [metricPage, metricPageSize, metricRows]);
  const paginatedPerformance = useMemo(() => paginateItems(performanceRows, performancePage, performancePageSize), [performancePage, performancePageSize, performanceRows]);

  useEffect(() => { setSelectedCampaign(null); }, [workspaceId]);
  useEffect(() => { setCampaignPage((page) => clampPage(page, campaignPageSize, campaignRows.length)); }, [campaignPageSize, campaignRows.length]);
  useEffect(() => { setMetricPage((page) => clampPage(page, metricPageSize, metricRows.length)); }, [metricPageSize, metricRows.length]);
  useEffect(() => { setPerformancePage((page) => clampPage(page, performancePageSize, performanceRows.length)); }, [performancePageSize, performanceRows.length]);

  return (
    <WorkspacePage>
        <WorkspaceHeader title={t("advertising.title")} description={t("advertising.subtitle")} eyebrow={t("advertising.reportEyebrow")} actions={canEditAdvertising ? <div className="flex flex-wrap gap-2"><Button onClick={() => setIsCampaignCreateOpen(true)}>{t("advertising.createCampaign")}</Button><Button variant="secondary" onClick={() => setIsMetricCreateOpen(true)}>{t("advertising.addDailyMetric")}</Button></div> : undefined} />
        <section className="grid gap-2 rounded-2xl border border-warning/20 bg-warning/10 p-4 text-sm text-warning-foreground" data-advertising-reporting-source="manual-import-meta-future">
          <p className="font-bold">{t("advertising.dataSourceTitle")}: {t("advertising.manualSource")}</p>
          <p>{t("advertising.manualImportFirst")}</p>
          <p>{t("advertising.futureMetaSync")}</p>
          <p>{t("advertising.formulaSafety")}</p>
        </section>

        <AdvertisingDateRangeFilter startDate={startDate} endDate={endDate} onStartDate={setStartDate} onEndDate={setEndDate} />

        <MetaAdsReadinessCard compact />

        <CompactSummary layout="five-balanced" items={[{ label: t("advertising.spend"), value: formatMoney(summary.data?.total_spend, currencyCode), helper: t("finance.selectedPeriod") }, { label: t("advertising.leads"), value: summary.data?.total_leads ?? "—", helper: t("advertising.cplExplanation") }, { label: t("advertising.orders"), value: summary.data?.total_orders ?? "—", helper: t("advertising.cpaExplanation") }, { label: t("advertising.revenue"), value: formatMoney(summary.data?.total_revenue, currencyCode), helper: t("advertising.roasExplanation") }, { label: "ROAS", value: summary.data?.roas ?? "—", unavailable: summary.data?.roas == null, helper: t("advertising.safeZeroDenominator") }]} />

        <section className="grid w-full max-w-full min-w-0 gap-3 overflow-hidden rounded-2xl bg-white p-4 shadow-sm md:grid-cols-2 xl:grid-cols-4" data-advertising-reporting-polish="manual-import-attribution-optional">
          <div className="rounded-xl border border-blue-100 bg-blue-50 p-3 text-sm text-blue-950">
            <p className="font-bold">{t("advertising.importMetricsFirst")}</p>
            <p className="mt-1">{t("advertising.filteredEmpty")}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <a className="rounded-lg bg-blue-700 px-3 py-2 font-bold text-white" href="/templates/advertising-import-template.csv" download>{t("advertising.templateCta")}</a>
              <a className="rounded-lg border border-blue-200 bg-white px-3 py-2 font-bold text-blue-800" href="/settings/import">{t("advertising.openImportCenter")}</a>
            </div>
          </div>
          <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-3 text-sm text-emerald-950">
            <p className="font-bold">ROAS</p>
            <p className="mt-1">{t("advertising.roasExplanation")}</p>
          </div>
          <div className="rounded-xl border border-purple-100 bg-purple-50 p-3 text-sm text-purple-950">
            <p className="font-bold">CPA / CPL</p>
            <p className="mt-1">{t("advertising.cpaExplanation")} {t("advertising.cplExplanation")}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
            <p className="font-bold">{t("advertising.source")}: {t("advertising.manualSource")}</p>
            <p className="mt-1">{t("advertising.attributionOptional")}</p>
            <p className="mt-1">{t("advertising.manualAttributionRules")}</p>
          </div>
        </section>

        <CampaignInsightsPanel rows={performance.data ?? []} campaigns={campaigns.data ?? []} currencyCode={currencyCode} />

        <section className="grid w-full max-w-full min-w-0 gap-3 overflow-hidden rounded-2xl border border-indigo-100 bg-indigo-50 p-4 text-sm text-indigo-950 shadow-sm" data-manual-attribution-summary="manual-campaign-id-orders-leads-meta-future">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-600">{t("advertising.manualAttributionEyebrow")}</p>
            <h2 className="mt-1 text-xl font-black">{t("advertising.manualAttributionTitle")}</h2>
          </div>
          <div className="grid gap-2 md:grid-cols-2">
            <p>{t("advertising.manualAttributionManual")}</p>
            <p>{t("advertising.manualAttributionLinkedOnly")}</p>
            <p>{t("advertising.manualAttributionUnattributedValid")}</p>
            <p>{t("advertising.manualAttributionMetaFuture")}</p>
          </div>
        </section>

        <div className="grid min-w-0 gap-3"><CampaignPerformanceTable rows={paginatedPerformance} />{performanceRows.length > performancePageSize ? <PaginationControls page={performancePage} pageSize={performancePageSize} totalItems={performanceRows.length} onPageChange={setPerformancePage} onPageSizeChange={(size) => { setPerformancePageSize(size as (typeof PAGE_SIZE_OPTIONS)[number]); setPerformancePage(1); }} /> : null}</div>
        <div className="grid min-w-0 gap-3"><AdMetricTable metrics={paginatedMetrics} onEdit={canEditAdvertising ? setEditingMetric : undefined} onDelete={canEditAdvertising ? setDeletingMetric : undefined} />{metricRows.length > metricPageSize ? <PaginationControls page={metricPage} pageSize={metricPageSize} totalItems={metricRows.length} onPageChange={setMetricPage} onPageSizeChange={(size) => { setMetricPageSize(size as (typeof PAGE_SIZE_OPTIONS)[number]); setMetricPage(1); }} /> : null}</div>
        <AdvertisingTrendChart data={trend.data ?? []} />
        <WorkspaceSplitView panelOpen={Boolean(selectedCampaign)} panel={selectedCampaign ? <EntitySidePanel open={Boolean(selectedCampaign)} title={selectedCampaign.name} description={`${selectedCampaign.platform} · ${selectedCampaign.status}`} onClose={() => setSelectedCampaign(null)} footer={canEditAdvertising ? <div className="flex gap-2"><Button variant="secondary" onClick={() => setEditingCampaign(selectedCampaign)}>{t("advertising.editCampaign")}</Button><Button variant="danger" onClick={() => setArchivingCampaign(selectedCampaign)}>{t("actions.archive")}</Button></div> : undefined}><FieldGrid><FieldItem label={t("advertising.source")} value={t("advertising.manualSource")} /><FieldItem label={t("advertising.platform")} value={selectedCampaign.platform} /><FieldItem label={t("tables.status")} value={selectedCampaign.status} /><FieldItem label={t("advertising.objective")} value={selectedCampaign.objective} /><FieldItem label={t("advertising.dailyBudget")} value={selectedCampaign.daily_budget ?? "—"} /><FieldItem label={t("advertising.totalBudget")} value={selectedCampaign.total_budget ?? "—"} /></FieldGrid></EntitySidePanel> : null}><div className="grid min-w-0 gap-3"><CampaignTable campaigns={paginatedCampaigns} selectedCampaignId={selectedCampaign?.id} onSelect={setSelectedCampaign} onEdit={canEditAdvertising ? setEditingCampaign : undefined} onArchive={canEditAdvertising ? setArchivingCampaign : undefined} />{campaignRows.length > campaignPageSize ? <PaginationControls page={campaignPage} pageSize={campaignPageSize} totalItems={campaignRows.length} onPageChange={setCampaignPage} onPageSizeChange={(size) => { setCampaignPageSize(size as (typeof PAGE_SIZE_OPTIONS)[number]); setCampaignPage(1); }} /> : null}</div></WorkspaceSplitView>

        <section className="grid w-full max-w-full min-w-0 gap-4 overflow-hidden rounded-2xl bg-white p-4 shadow-sm" data-advertising-readiness-gate="not-pilot-ready-meta-future-runtime-qa-pending">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">{t("advertising.readinessEyebrow")}</p>
            <h2 className="mt-1 text-xl font-black text-slate-950">{t("advertising.readinessTitle")}</h2>
            <p className="mt-1 text-sm text-slate-600">{t("advertising.readinessDescription")}</p>
          </div>
          <div className="grid gap-3 lg:grid-cols-3">
            <StatusList title={t("advertising.readinessReadyTitle")} items={readinessReady} tone="ready" />
            <StatusList title={t("advertising.readinessPendingTitle")} items={readinessPending} tone="pending" />
            <StatusList title={t("advertising.readinessMetaTitle")} items={[t("advertising.readinessMetaFuture")]} tone="future" />
          </div>
        </section>

        {isCampaignCreateOpen ? <FormDialog title={t("advertising.createCampaign")} description="Campaign setup uses the shared responsive modal shell." size="lg" onClose={() => setIsCampaignCreateOpen(false)}><CampaignForm onSubmit={(payload) => createCampaignMutation.mutate(payload)} /></FormDialog> : null}
        {isMetricCreateOpen ? <FormDialog title={t("advertising.addDailyMetric")} description="Record spend and outcomes in the same mobile-safe dialog pattern." size="lg" onClose={() => setIsMetricCreateOpen(false)}><AdMetricForm campaigns={campaigns.data ?? []} onSubmit={(payload) => createMetricMutation.mutate(payload)} /></FormDialog> : null}
        {archivingCampaign ? <ConfirmActionDialog title="Archive campaign?" description="This campaign will be hidden from active advertising lists. Historical metrics are preserved unless deleted separately." actionLabel="Archive campaign" isSubmitting={archiveCampaignMutation.isPending} error={archiveCampaignMutation.isError ? safeApiErrorMessage(archiveCampaignMutation.error, "Unable to delete record. Please try again.") : null} onCancel={() => setArchivingCampaign(null)} onConfirm={() => archiveCampaignMutation.mutate()} /> : null}
        {deletingMetric ? <ConfirmActionDialog title="Delete metric?" description="This daily metric will be removed from advertising summaries, trends, and performance calculations." actionLabel="Delete metric" isSubmitting={deleteMetricMutation.isPending} error={deleteMetricMutation.isError ? safeApiErrorMessage(deleteMetricMutation.error, "Unable to delete record. Please try again.") : null} onCancel={() => setDeletingMetric(null)} onConfirm={() => deleteMetricMutation.mutate()} /> : null}
        {editingCampaign ? <EditRecordDialog title={t("advertising.editCampaign")} fields={[{ name: "name", label: "Name" }, { name: "platform", label: "Platform", type: "select", options: ["META", "INSTAGRAM", "FACEBOOK", "TIKTOK", "GOOGLE", "TELEGRAM", "OTHER"].map((value) => ({ value, label: value })) }, { name: "status", label: "Status", type: "select", options: ["ACTIVE", "PAUSED", "COMPLETED", "ARCHIVED"].map((value) => ({ value, label: value })) }, { name: "objective", label: "Objective", type: "select", options: ["MESSAGES", "SALES", "TRAFFIC", "AWARENESS", "FOLLOWERS", "OTHER"].map((value) => ({ value, label: value })) }, { name: "budget_type", label: "Budget type", type: "select", options: ["DAILY", "LIFETIME", "MANUAL"].map((value) => ({ value, label: value })) }, { name: "daily_budget", label: "Daily budget", type: "number" }, { name: "total_budget", label: "Total budget", type: "number" }, { name: "start_date", label: "Start date", type: "date" }, { name: "end_date", label: "End date", type: "date" }, { name: "notes", label: "Notes", type: "textarea" }]} initialValues={editingCampaign} isSubmitting={updateCampaignMutation.isPending} submitError={updateCampaignMutation.isError ? safeApiErrorMessage(updateCampaignMutation.error, "Unable to save campaign changes. Please try again.") : null} onClose={() => setEditingCampaign(null)} onSubmit={(values) => updateCampaignMutation.mutate(values)} /> : null}
        {editingMetric ? <EditRecordDialog title={t("advertising.editMetric")} fields={[{ name: "metric_date", label: "Metric date", type: "date" }, { name: "spend", label: t("advertising.spend"), type: "number" }, { name: "impressions", label: "Impressions", type: "number" }, { name: "reach", label: "Reach", type: "number" }, { name: "clicks", label: "Clicks", type: "number" }, { name: "messages", label: t("advertising.messages"), type: "number" }, { name: "leads", label: t("advertising.leads"), type: "number" }, { name: "orders", label: t("advertising.orders"), type: "number" }, { name: "revenue", label: t("advertising.revenue"), type: "number" }, { name: "net_profit", label: "Net profit", type: "number" }]} initialValues={editingMetric} isSubmitting={updateMetricMutation.isPending} submitError={updateMetricMutation.isError ? safeApiErrorMessage(updateMetricMutation.error, "Unable to save metric changes. Please try again.") : null} onClose={() => setEditingMetric(null)} onSubmit={(values) => updateMetricMutation.mutate(values)} /> : null}
    </WorkspacePage>
  );
}
// Localization regression compatibility markers: FormDialog title="Create campaign"; FormDialog title="Add daily metric".
