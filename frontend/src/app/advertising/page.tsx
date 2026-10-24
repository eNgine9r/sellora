"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, CalendarDays, ChevronDown, Download, Plus, RefreshCw, SlidersHorizontal } from "lucide-react";
import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
import { EditRecordDialog } from "@/components/edit-record-dialog";
import { FormDialog } from "@/components/form-dialog";
import { AdMetricForm } from "@/features/advertising/components/ad-metric-form";
import { AdMetricTable } from "@/features/advertising/components/ad-metric-table";
import { AdvertisingDateRangeFilter } from "@/features/advertising/components/advertising-date-range-filter";
import { AdvertisingTrendChart } from "@/features/advertising/components/advertising-trend-chart";
import { AdvertisingDashboardOverview } from "@/features/advertising/components/advertising-dashboard-overview";
import { CrmAttributionPanel } from "@/features/advertising/components/crm-attribution-panel";
import { CampaignForm } from "@/features/advertising/components/campaign-form";
import { CampaignPerformanceTable } from "@/features/advertising/components/campaign-performance-table";
import { CampaignTable } from "@/features/advertising/components/campaign-table";
import { buildAdCampaignUpdatePayload, buildAdMetricUpdatePayload } from "@/lib/payload-builders";
import { safeApiErrorMessage } from "@/services/api";
import { createAdCampaign, createAdMetric, deleteAdCampaign, deleteAdMetric, fetchAdCampaigns, fetchAdMetrics, fetchAdvertisingSummary, fetchAdvertisingTrend, fetchCampaignPerformance, updateAdCampaign, updateAdMetric } from "@/services/advertising";
import { AdCampaign, AdCampaignCreate, AdMetric, AdMetricCreate } from "@/types/advertising";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { MetaAdsReadinessCard } from "@/features/integrations/components/meta-ads-readiness-card";
import { Button, EntitySidePanel, FieldGrid, FieldItem, WorkspaceHeader, WorkspacePage, WorkspaceSplitView } from "@/components/crm-workspace";
import { PaginationControls, PAGE_SIZE_OPTIONS, clampPage, paginateItems } from "@/components/pagination-controls";

const PLATFORM_OPTIONS = [["META", "Meta"], ["INSTAGRAM", "Instagram"], ["FACEBOOK", "Facebook"], ["TIKTOK", "TikTok"], ["GOOGLE", "Google"], ["TELEGRAM", "Telegram"], ["OTHER", "Інше"]].map(([value, label]) => ({ value, label }));
const STATUS_OPTIONS = [["ACTIVE", "Активна"], ["PAUSED", "Призупинена"], ["COMPLETED", "Завершена"], ["ARCHIVED", "Архівна"]].map(([value, label]) => ({ value, label }));
const OBJECTIVE_OPTIONS = [["MESSAGES", "Повідомлення"], ["SALES", "Продажі"], ["TRAFFIC", "Трафік"], ["AWARENESS", "Впізнаваність"], ["FOLLOWERS", "Підписники"], ["OTHER", "Інше"]].map(([value, label]) => ({ value, label }));
const BUDGET_OPTIONS = [["DAILY", "Денний"], ["LIFETIME", "На весь період"], ["MANUAL", "Ручний"]].map(([value, label]) => ({ value, label }));

type PeriodPreset = "7" | "30" | "90" | "all" | "custom";
type AdvertisingTab = "overview" | "campaigns" | "data";

function localIsoDate(date: Date) {
  const y = date.getFullYear();
  return String(y) + "-" + String(date.getMonth() + 1).padStart(2, "0") + "-" + String(date.getDate()).padStart(2, "0");
}

function periodDates(days: number): [string, string] {
  const end = new Date();
  const start = new Date(end);
  start.setDate(end.getDate() - (days - 1));
  return [localIsoDate(start), localIsoDate(end)];
}

export default function AdvertisingPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspace, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const currencyCode = currentWorkspace?.currency_code ?? "UAH";
  const [startDate, setStartDate] = useState(() => periodDates(30)[0]);
  const [endDate, setEndDate] = useState(() => periodDates(30)[1]);
  const [periodPreset, setPeriodPreset] = useState<PeriodPreset>("30");
  const [activeTab, setActiveTab] = useState<AdvertisingTab>("overview");
  const [campaignSearch, setCampaignSearch] = useState("");
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
  const performance = useQuery({ queryKey: ["ad-performance", workspaceId, startDate, endDate], queryFn: () => fetchCampaignPerformance(workspaceId, undefined, startDate, endDate, 100), enabled });
  const trend = useQuery({ queryKey: ["ad-trend", workspaceId, startDate, endDate], queryFn: () => fetchAdvertisingTrend(workspaceId, undefined, startDate, endDate), enabled });
  const hasMetaMetrics = Boolean(metrics.data?.some(row => row.source_type === "meta_live" && (!startDate || row.metric_date >= startDate) && (!endDate || row.metric_date <= endDate)));
  const hasManualMetrics = Boolean(metrics.data?.some(row => row.source_type !== "meta_live" && (!startDate || row.metric_date >= startDate) && (!endDate || row.metric_date <= endDate)));
  const sourceLabel = t(hasMetaMetrics && hasManualMetrics ? "advertising.mixedSource" : hasMetaMetrics ? "adsDashboard.metaSource" : "adsDashboard.manualSource");
  const invalidateAds = () => {
    queryClient.invalidateQueries({ queryKey: ["ad-campaigns", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["ad-metrics", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["ad-summary", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["ad-performance", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["ad-trend", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["ad-crm-attribution", workspaceId] });
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
  const filteredPerformance = useMemo(() => performanceRows.filter(row =>
    row.campaign_name.toLocaleLowerCase().includes(campaignSearch.trim().toLocaleLowerCase())
  ), [performanceRows, campaignSearch]);
  const paginatedPerformance = useMemo(() => paginateItems(filteredPerformance, performancePage, performancePageSize), [performancePage, performancePageSize, filteredPerformance]);

  useEffect(() => { setSelectedCampaign(null); }, [workspaceId]);
  function selectPeriod(preset: PeriodPreset) {
    setPeriodPreset(preset);
    if (preset === "all") { setStartDate("2000-01-01"); setEndDate(localIsoDate(new Date())); }
    else if (preset !== "custom") {
      const [start, end] = periodDates(Number(preset));
      setStartDate(start);
      setEndDate(end);
    }
  }

  useEffect(() => { setCampaignPage((page) => clampPage(page, campaignPageSize, campaignRows.length)); }, [campaignPageSize, campaignRows.length]);
  useEffect(() => { setMetricPage((page) => clampPage(page, metricPageSize, metricRows.length)); }, [metricPageSize, metricRows.length]);
  useEffect(() => { setPerformancePage((page) => clampPage(page, performancePageSize, filteredPerformance.length)); }, [performancePageSize, filteredPerformance.length]);

  return (
    <WorkspacePage>
      <WorkspaceHeader title={t("advertising.title")} description={t("adsDashboard.pageDescription")} eyebrow={t("adsDashboard.eyebrow")} />
      <section className="relative isolate grid min-w-0 gap-4 overflow-hidden rounded-3xl border border-indigo-400/20 bg-gradient-to-br from-[#1f164d] via-[#211c47] to-[#11182b] p-5 text-white shadow-lg shadow-indigo-500/5 sm:p-7" data-advertising-overview-hero>
        <div aria-hidden="true" className="pointer-events-none absolute -right-14 -top-24 -z-10 size-72 rounded-full bg-violet-500/20 blur-3xl" />
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-medium text-indigo-100">
              <span className="size-2 rounded-full bg-emerald-400" />{sourceLabel}
            </span>
            <h2 className="mt-4 text-2xl font-bold tracking-tight sm:text-3xl">{t("adsDashboard.heroTitle")}</h2>
            <p className="mt-2 max-w-xl text-sm leading-6 text-slate-300">{t("adsDashboard.heroSubtitle")}</p>
          </div>
          <Link href="/settings/integrations" className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-white/15 bg-white/10 px-3 text-sm font-semibold text-white transition hover:bg-white/20">
            <SlidersHorizontal className="size-4" aria-hidden="true" />{t("adsDashboard.integrations")}<ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        </div>
      </section>

      <section className="flex min-w-0 flex-wrap items-center gap-2" aria-label={t("adsDashboard.period")} data-advertising-period-presets>
        <CalendarDays className="mr-1 size-4 shrink-0 text-text-secondary" aria-hidden="true" />
        {(["7", "30", "90", "all", "custom"] as PeriodPreset[]).map(preset => (
          <button key={preset} type="button" aria-pressed={periodPreset === preset}
            className={"min-h-10 rounded-xl border px-3.5 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 " +
              (periodPreset === preset ? "border-indigo-500 bg-indigo-600 text-white shadow-sm" : "border-border-subtle bg-surface-1 text-text-secondary hover:bg-surface-2")}
            onClick={() => selectPeriod(preset)}>{t("adsDashboard.period_" + preset)}</button>
        ))}
      </section>
      {periodPreset === "custom" ? <AdvertisingDateRangeFilter startDate={startDate} endDate={endDate}
        onStartDate={value => { setStartDate(value); setPeriodPreset("custom"); }}
        onEndDate={value => { setEndDate(value); setPeriodPreset("custom"); }} /> : null}

      {summary.isError || performance.isError || trend.isError || metrics.isError ? (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-text-primary">
          <p>{t("adsDashboard.loadError")}</p>
          <button type="button" className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-border-subtle bg-surface-1 px-3 font-semibold"
            onClick={() => { void Promise.all([summary.refetch(), performance.refetch(), trend.refetch(), metrics.refetch()]); }}>
            <RefreshCw className="size-4" aria-hidden="true" />{t("adsDashboard.retry")}
          </button>
        </div>
      ) : null}

      <AdvertisingDashboardOverview summary={summary.data} campaigns={performanceRows} currencyCode={currencyCode}
        sourceLabel={sourceLabel} loading={summary.isPending || metrics.isPending} />
      <AdvertisingTrendChart data={trend.data ?? []} currencyCode={currencyCode} />

      <nav className="flex min-w-0 flex-wrap gap-1 rounded-2xl border border-border-subtle bg-surface-1 p-1.5" aria-label={t("adsDashboard.sections")}>
        {(["overview", "campaigns", "data"] as AdvertisingTab[]).map(tab => (
          <button key={tab} type="button" aria-current={activeTab === tab ? "page" : undefined}
            className={"min-h-11 flex-1 rounded-xl px-4 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500 sm:flex-none " +
              (activeTab === tab ? "bg-indigo-600 text-white shadow-sm" : "text-text-secondary hover:bg-surface-2")}
            onClick={() => setActiveTab(tab)}>{t("adsDashboard.tab_" + tab)}</button>
        ))}
      </nav>

      {activeTab === "overview" ? (
        <CrmAttributionPanel
          workspaceId={workspaceId} startDate={startDate} endDate={endDate}
          currencyCode={currencyCode} enabled={enabled}
        />
      ) : null}

      {activeTab === "overview" ? (
        <section className="grid min-w-0 gap-3 rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm sm:p-5" data-advertising-next-actions>
          <h2 className="text-base font-semibold text-text-primary">{t("adsDashboard.nextStepsTitle")}</h2>
          <p className="text-sm leading-6 text-text-secondary">{t("adsDashboard.nextStepsDescription")}</p>
          <button type="button" className="inline-flex min-h-11 w-fit items-center gap-2 rounded-xl border border-border-subtle bg-surface-2 px-4 text-sm font-semibold text-text-primary hover:bg-surface-hover"
            onClick={() => setActiveTab("campaigns")}>{t("adsDashboard.viewCampaigns")}<ArrowRight className="size-4" aria-hidden="true" /></button>
        </section>
      ) : null}

      {activeTab === "campaigns" ? (
        <div className="grid min-w-0 gap-4" data-advertising-campaigns-view>
          <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-text-primary">{t("adsDashboard.campaignsTitle")}</h2>
              <p className="text-xs text-text-secondary">{t("adsDashboard.campaignsCaption")}</p>
            </div>
            <label className="min-w-0 sm:w-64">
              <span className="sr-only">{t("adsDashboard.searchCampaigns")}</span>
              <input type="search" value={campaignSearch} onChange={event => { setCampaignSearch(event.target.value); setPerformancePage(1); }}
                placeholder={t("adsDashboard.searchCampaigns")}
                className="min-h-11 w-full min-w-0 rounded-xl border border-input-border bg-input-background px-3 text-sm text-text-primary" />
            </label>
          </div>
          <CampaignPerformanceTable rows={paginatedPerformance} currencyCode={currencyCode} />
          {filteredPerformance.length > performancePageSize ? <PaginationControls page={performancePage} pageSize={performancePageSize}
            totalItems={filteredPerformance.length} onPageChange={setPerformancePage}
            onPageSizeChange={size => { setPerformancePageSize(size as (typeof PAGE_SIZE_OPTIONS)[number]); setPerformancePage(1); }} /> : null}
          <p className="rounded-xl border border-border-subtle bg-surface-2 p-4 text-sm leading-6 text-text-secondary" data-advertising-attribution-disclaimer>{t("adsDashboard.attributionNotice")}</p>
        </div>
      ) : null}

      {activeTab === "data" ? (
        <div className="grid min-w-0 gap-4" data-advertising-data-view>
          <section className="grid min-w-0 gap-3 rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm sm:p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div><h2 className="text-base font-bold text-text-primary">{t("adsDashboard.manageData")}</h2><p className="mt-1 text-sm text-text-secondary">{t("adsDashboard.manageDataHint")}</p></div>
              {canEditAdvertising ? <div className="flex flex-wrap gap-2">
                <Button onClick={() => setIsCampaignCreateOpen(true)}><Plus className="mr-1 inline size-4" />{t("advertising.createCampaign")}</Button>
                <Button variant="secondary" onClick={() => setIsMetricCreateOpen(true)}>{t("advertising.addDailyMetric")}</Button>
              </div> : null}
            </div>
            <a className="inline-flex min-h-10 w-fit items-center gap-2 text-sm font-semibold text-indigo-600 hover:underline dark:text-indigo-300"
              href="/templates/advertising-import-template.csv" download><Download className="size-4" aria-hidden="true" />{t("advertising.templateCta")}</a>
            <Link href="/settings/import" className="text-sm font-medium text-text-secondary hover:underline">{t("advertising.openImportCenter")}</Link>
          </section>

          <details className="min-w-0 rounded-2xl border border-border-subtle bg-surface-1 p-4" data-advertising-connection-settings>
            <summary className="flex min-h-10 cursor-pointer items-center gap-2 text-sm font-semibold text-text-primary">
              <ChevronDown className="size-4" aria-hidden="true" />{t("adsDashboard.metaConnection")}
            </summary>
            <div className="mt-4"><MetaAdsReadinessCard compact /></div>
          </details>
          <div className="grid min-w-0 gap-3">
            <AdMetricTable metrics={paginatedMetrics} onEdit={canEditAdvertising ? setEditingMetric : undefined} onDelete={canEditAdvertising ? setDeletingMetric : undefined} />
            {metricRows.length > metricPageSize ? <PaginationControls page={metricPage} pageSize={metricPageSize} totalItems={metricRows.length}
              onPageChange={setMetricPage} onPageSizeChange={size => { setMetricPageSize(size as (typeof PAGE_SIZE_OPTIONS)[number]); setMetricPage(1); }} /> : null}
          </div>
          <WorkspaceSplitView panelOpen={Boolean(selectedCampaign)} panel={selectedCampaign ? <EntitySidePanel open={Boolean(selectedCampaign)} title={selectedCampaign.name} description={`${selectedCampaign.platform} · ${selectedCampaign.status}`} onClose={() => setSelectedCampaign(null)} footer={canEditAdvertising ? <div className="flex gap-2"><Button variant="secondary" onClick={() => setEditingCampaign(selectedCampaign)}>{t("advertising.editCampaign")}</Button><Button variant="danger" onClick={() => setArchivingCampaign(selectedCampaign)}>{t("actions.archive")}</Button></div> : undefined}><FieldGrid><FieldItem label={t("advertising.source")} value={t("advertising.campaignMetricsSource")} /><FieldItem label={t("advertising.platform")} value={selectedCampaign.platform} /><FieldItem label={t("tables.status")} value={selectedCampaign.status} /><FieldItem label={t("advertising.objective")} value={selectedCampaign.objective} /><FieldItem label={t("advertising.dailyBudget")} value={selectedCampaign.daily_budget ?? "—"} /><FieldItem label={t("advertising.totalBudget")} value={selectedCampaign.total_budget ?? "—"} /></FieldGrid></EntitySidePanel> : null}><div className="grid min-w-0 gap-3"><CampaignTable campaigns={paginatedCampaigns} selectedCampaignId={selectedCampaign?.id} onSelect={setSelectedCampaign} onEdit={canEditAdvertising ? setEditingCampaign : undefined} onArchive={canEditAdvertising ? setArchivingCampaign : undefined} />{campaignRows.length > campaignPageSize ? <PaginationControls page={campaignPage} pageSize={campaignPageSize} totalItems={campaignRows.length} onPageChange={setCampaignPage} onPageSizeChange={(size) => { setCampaignPageSize(size as (typeof PAGE_SIZE_OPTIONS)[number]); setCampaignPage(1); }} /> : null}</div></WorkspaceSplitView>
        </div>
      ) : null}
      {isCampaignCreateOpen ? <FormDialog title={t("advertising.createCampaign")} description="Налаштуйте кампанію, бюджет, період і ціль реклами." size="lg" onClose={() => setIsCampaignCreateOpen(false)}><CampaignForm onSubmit={(payload) => createCampaignMutation.mutate(payload)} /></FormDialog> : null}
      {isMetricCreateOpen ? <FormDialog title={t("advertising.addDailyMetric")} description="Внесіть витрати та результати за один день." size="lg" onClose={() => setIsMetricCreateOpen(false)}><AdMetricForm campaigns={campaigns.data ?? []} onSubmit={(payload) => createMetricMutation.mutate(payload)} /></FormDialog> : null}
      {archivingCampaign ? <ConfirmActionDialog title="Архівувати кампанію?" description="Кампанію буде приховано з активних списків. Історичні метрики залишаться збереженими." actionLabel="Архівувати кампанію" isSubmitting={archiveCampaignMutation.isPending} error={archiveCampaignMutation.isError ? safeApiErrorMessage(archiveCampaignMutation.error, "Не вдалося архівувати кампанію. Спробуйте ще раз.") : null} onCancel={() => setArchivingCampaign(null)} onConfirm={() => archiveCampaignMutation.mutate()} /> : null}
      {deletingMetric ? <ConfirmActionDialog title="Видалити метрику?" description="Денну метрику буде видалено з підсумків, трендів і розрахунків ефективності." actionLabel="Видалити метрику" isSubmitting={deleteMetricMutation.isPending} error={deleteMetricMutation.isError ? safeApiErrorMessage(deleteMetricMutation.error, "Не вдалося видалити метрику. Спробуйте ще раз.") : null} onCancel={() => setDeletingMetric(null)} onConfirm={() => deleteMetricMutation.mutate()} /> : null}
      {editingCampaign ? <EditRecordDialog title={t("advertising.editCampaign")} fields={[{ name: "name", label: t("advertising.campaignName") }, { name: "platform", label: t("advertising.platform"), type: "select", options: PLATFORM_OPTIONS }, { name: "status", label: t("tables.status"), type: "select", options: STATUS_OPTIONS }, { name: "objective", label: t("advertising.objective"), type: "select", options: OBJECTIVE_OPTIONS }, { name: "budget_type", label: "Тип бюджету", type: "select", options: BUDGET_OPTIONS }, { name: "daily_budget", label: t("advertising.dailyBudget"), type: "number" }, { name: "total_budget", label: t("advertising.totalBudget"), type: "number" }, { name: "start_date", label: "Дата початку", type: "date" }, { name: "end_date", label: "Дата завершення", type: "date" }, { name: "notes", label: t("advertising.notes"), type: "textarea" }]} initialValues={editingCampaign} isSubmitting={updateCampaignMutation.isPending} submitError={updateCampaignMutation.isError ? safeApiErrorMessage(updateCampaignMutation.error, "Не вдалося зберегти зміни кампанії.") : null} onClose={() => setEditingCampaign(null)} onSubmit={(values) => updateCampaignMutation.mutate(values)} /> : null}
      {editingMetric ? <EditRecordDialog title={t("advertising.editMetric")} fields={[{ name: "metric_date", label: "Дата метрики", type: "date" }, { name: "spend", label: t("advertising.spend"), type: "number" }, { name: "impressions", label: "Покази", type: "number" }, { name: "reach", label: "Охоплення", type: "number" }, { name: "clicks", label: "Кліки", type: "number" }, { name: "messages", label: t("advertising.messages"), type: "number" }, { name: "leads", label: t("advertising.leads"), type: "number" }, { name: "orders", label: t("advertising.orders"), type: "number" }, { name: "revenue", label: t("advertising.revenue"), type: "number" }, { name: "net_profit", label: t("finance.netProfit"), type: "number" }]} initialValues={editingMetric} isSubmitting={updateMetricMutation.isPending} submitError={updateMetricMutation.isError ? safeApiErrorMessage(updateMetricMutation.error, "Не вдалося зберегти зміни метрики.") : null} onClose={() => setEditingMetric(null)} onSubmit={(values) => updateMetricMutation.mutate(values)} /> : null}
    </WorkspacePage>
  );
}
