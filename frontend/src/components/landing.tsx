"use client";

import { BarChart3, Boxes, CheckCircle2, Megaphone, MessageCircle, PackageCheck, Repeat2, ShoppingBag, Truck, Users, WalletCards } from "lucide-react";
import { Button, Card } from "@/components/ui/primitives";
import { IntegrationStatusBadge, MarketingCTA, PublicFooter, PublicHeader, PublicPageContainer, PublicSection } from "@/components/public-layout";
import { useI18n } from "@/i18n/provider";

type PreviewMetric = { label: string; value: string; helper: string };
type WorkflowStep = { title: string; description: string };
type Capability = { title: string; description: string };
type Integration = { title: string; description: string; status: "available" | "pilot" | "beta" | "soon" | "notConnected" };

const workflowIcons = [MessageCircle, Users, ShoppingBag, WalletCards, Truck, BarChart3, Repeat2];
const capabilityIcons = [Users, ShoppingBag, Boxes, Truck, Megaphone, BarChart3];

function TrustPoint({ children }: { children: string }) {
  return <span className="inline-flex min-h-9 items-center gap-2 rounded-full border border-border-subtle bg-surface-1 px-3 text-sm font-bold text-text-secondary"><CheckCircle2 className="h-4 w-4 text-violet-300" aria-hidden="true" />{children}</span>;
}

function ProductPreview() {
  const { t, tr } = useI18n();
  const metrics = tr<PreviewMetric[]>("landing.preview.metrics");
  const funnel = tr<string[]>("landing.preview.funnel");
  const orders = tr<string[]>("landing.preview.orders");
  return (
    <div className="relative w-full min-w-0 max-w-full overflow-hidden" aria-label={t("landing.preview.ariaLabel")}>
      <div className="pointer-events-none absolute -inset-2 rounded-[2rem] bg-brand-gradient opacity-20 blur-3xl sm:-inset-6" aria-hidden="true" />
      <Card className="relative min-w-0 overflow-hidden p-3 sm:p-5">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div>
            <p className="text-sm font-black text-text-primary">{t("landing.previewTitle")}</p>
            <p className="mt-1 text-xs font-semibold text-text-muted">{t("landing.previewSubtitle")}</p>
          </div>
          <span className="rounded-full border border-warning/30 bg-warning/10 px-3 py-1 text-xs font-black text-amber-200">{t("landing.preview.demo")}</span>
        </div>
        <div className="mt-5 grid min-w-0 gap-3 sm:grid-cols-3">
          {metrics.map((metric) => <div key={metric.label} className="min-w-0 rounded-2xl border border-border-subtle bg-surface-2 p-3"><p className="truncate text-xs font-bold text-text-muted">{metric.label}</p><p className="mt-2 text-2xl font-black text-text-primary">{metric.value}</p><p className="mt-1 text-xs font-semibold text-text-secondary">{metric.helper}</p></div>)}
        </div>
        <div className="mt-4 grid min-w-0 gap-4 lg:grid-cols-[1fr_0.9fr]">
          <div className="min-w-0 rounded-3xl border border-border-subtle bg-surface-2 p-3 sm:p-4">
            <div className="flex items-center justify-between gap-3"><p className="text-sm font-black text-text-primary">{t("landing.preview.funnelTitle")}</p><PackageCheck className="h-5 w-5 text-violet-300" aria-hidden="true" /></div>
            <div className="mt-4 grid gap-3">
              {funnel.map((item, index) => <div key={item} className="grid min-w-0 gap-1"><div className="flex items-center justify-between gap-2 text-xs font-bold text-text-secondary"><span className="min-w-0 truncate">{item}</span><span className="shrink-0">{96 - index * 12}%</span></div><div className="h-2.5 w-full overflow-hidden rounded-full bg-surface-3"><div className="h-full rounded-full bg-brand-gradient" style={{ width: `${96 - index * 12}%` }} aria-hidden="true" /></div></div>)}
            </div>
          </div>
          <div className="min-w-0 rounded-3xl border border-border-subtle bg-surface-2 p-3 sm:p-4">
            <p className="text-sm font-black text-text-primary">{t("landing.preview.ordersTitle")}</p>
            <div className="mt-4 grid gap-3">
              {orders.map((order) => <div key={order} className="grid min-w-0 gap-2 rounded-2xl bg-surface-3 px-3 py-2 text-sm sm:flex sm:items-center sm:justify-between"><span className="min-w-0 break-words font-bold text-text-secondary">{order}</span><span className="w-fit rounded-full bg-[var(--success-surface)] px-2 py-1 text-xs font-black text-[var(--success-foreground)]">{t("landing.preview.paid")}</span></div>)}
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

export function LandingPage() {
  const { t, tr } = useI18n();
  const trustPoints = tr<string[]>("landing.trustPoints");
  const workflow = tr<WorkflowStep[]>("landing.workflow");
  const capabilities = tr<Capability[]>("landing.capabilities.items");
  const integrations = tr<Integration[]>("landing.integrations.items");

  return (
    <PublicPageContainer>
      <PublicHeader />
      <main>
        <section className="relative overflow-hidden px-4 py-12 sm:px-6 lg:px-8 lg:py-20">
          <div className="pointer-events-none absolute left-1/2 top-[-220px] h-[420px] w-[min(760px,92vw)] -translate-x-1/2 rounded-full bg-brand-gradient opacity-25 blur-3xl" aria-hidden="true" />
          <div className="mx-auto grid max-w-7xl gap-10 lg:grid-cols-[0.95fr_1.05fr] lg:items-center">
            <div className="min-w-0">
              <p className="inline-flex rounded-full border border-border-subtle bg-surface-1 px-4 py-2 text-sm font-black uppercase tracking-[0.2em] text-violet-200">{t("landing.eyebrow")}</p>
              <h1 className="mt-6 max-w-4xl text-4xl font-black leading-[1.04] tracking-[-0.05em] text-text-primary sm:text-5xl lg:text-6xl">{t("landing.headline")}</h1>
              <p className="mt-5 max-w-2xl text-base leading-8 text-text-secondary sm:text-lg">{t("landing.subtitle")}</p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <MarketingCTA href="/login" className="w-full sm:w-auto">{t("landing.primaryCta")}</MarketingCTA>
                <Button variant="secondary" className="w-full sm:w-auto" type="button" onClick={() => document.getElementById("workflow")?.scrollIntoView({ behavior: "smooth", block: "start" })}>{t("landing.secondaryCta")}</Button>
              </div>
              <div className="mt-6 flex flex-wrap gap-2">{trustPoints.map((point) => <TrustPoint key={point}>{point}</TrustPoint>)}</div>
            </div>
            <ProductPreview />
          </div>
        </section>

        <PublicSection id="workflow" eyebrow={t("landing.workflowEyebrow")} title={t("landing.workflowTitle")} description={t("landing.workflowSubtitle")}>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-7">
            {workflow.map((step, index) => {
              const Icon = workflowIcons[index] ?? CheckCircle2;
              return <article key={step.title} className="rounded-[var(--radius-card)] border border-border-subtle bg-surface-1 p-4"><div className="flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-2xl bg-primary/15 text-violet-200"><Icon className="h-5 w-5" aria-hidden="true" /></div><span className="text-xs font-black text-text-muted">0{index + 1}</span></div><h3 className="mt-4 font-black text-text-primary">{step.title}</h3><p className="mt-2 text-sm leading-6 text-text-secondary">{step.description}</p></article>;
            })}
          </div>
        </PublicSection>

        <PublicSection id="capabilities" eyebrow={t("landing.capabilities.eyebrow")} title={t("landing.capabilities.title")} description={t("landing.capabilities.description")} className="pt-8">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {capabilities.map((capability, index) => {
              const Icon = capabilityIcons[index] ?? CheckCircle2;
              return <article key={capability.title} className="rounded-[var(--radius-card)] border border-border-subtle bg-surface-1 p-5 shadow-[var(--shadow-card)] transition hover:-translate-y-0.5 hover:bg-surface-2 motion-reduce:hover:translate-y-0"><div className="grid h-11 w-11 place-items-center rounded-2xl bg-surface-3 text-violet-200"><Icon className="h-5 w-5" aria-hidden="true" /></div><h3 className="mt-5 text-lg font-black text-text-primary">{capability.title}</h3><p className="mt-2 text-sm leading-6 text-text-secondary">{capability.description}</p></article>;
            })}
          </div>
        </PublicSection>

        <PublicSection id="integrations" eyebrow={t("landing.integrations.eyebrow")} title={t("landing.integrations.title")} description={t("landing.integrations.description")} className="pt-8">
          <div className="grid gap-4 md:grid-cols-3">
            {integrations.map((integration) => <article key={integration.title} className="rounded-[var(--radius-card)] border border-border-subtle bg-surface-1 p-5"><div className="flex items-start justify-between gap-4"><h3 className="text-lg font-black text-text-primary">{integration.title}</h3><IntegrationStatusBadge status={integration.status} /></div><p className="mt-3 text-sm leading-6 text-text-secondary">{integration.description}</p></article>)}
          </div>
        </PublicSection>

        <section className="px-4 py-16 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-5xl rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-6 text-center shadow-[var(--shadow-card)] sm:p-10">
            <p className="text-sm font-black uppercase tracking-[0.22em] text-violet-200">{t("landing.finalCtaEyebrow")}</p>
            <h2 className="mt-3 text-3xl font-black tracking-[-0.03em] text-text-primary sm:text-4xl">{t("landing.ctaTitle")}</h2>
            <p className="mx-auto mt-3 max-w-2xl text-text-secondary">{t("landing.ctaSubtitle")}</p>
            <div className="mt-6"><MarketingCTA href="/login">{t("landing.primaryCta")}</MarketingCTA></div>
          </div>
        </section>
      </main>
      <PublicFooter />
    </PublicPageContainer>
  );
}
// Localization regression compatibility marker: Операційна система для продажів з Instagram.
