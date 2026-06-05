import Link from "next/link";
import { ArrowRight, CheckCircle2, Sparkles } from "lucide-react";
import { BrandIcon, BrandLockup } from "@/components/brand";

const benefits = [
  ["Єдиний операційний центр", "Ліди, клієнти, замовлення, склад, відправлення й реклама зібрані в одному кабінеті."],
  ["Прибуток без таблиць", "Sellora показує дохід, витрати, ROAS та маржинальність так, щоб рішення було видно одразу."],
  ["Під staging-процеси", "Імпорт, ручні операції, архівування та workspace-логіка залишаються контрольованими."],
];

const workflow = ["Direct", "Lead", "Order", "Reserve", "Ship", "Profit"];

const features = [
  ["CRM", "Картки клієнтів, нотатки, теги, адреси та історія звернень."],
  ["Orders", "Мульти-item замовлення, редагування, статуси та прибутковість."],
  ["Inventory", "Залишки, резерви, incoming та low-stock контроль без оверфлоу."],
  ["Advertising", "Кампанії, щоденні метрики, ROAS, CPA та історичний імпорт."],
  ["Shipments", "Ручні відправлення, Nova Poshta foundation та TTN-контекст."],
  ["Analytics", "Dashboard, revenue, profit, top products та operational signals."],
];

export function LandingHero() {
  return (
    <section className="relative overflow-hidden bg-[#080812] text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_16%_10%,rgba(109,40,217,.35),transparent_34%),radial-gradient(circle_at_86%_12%,rgba(236,72,153,.22),transparent_30%),linear-gradient(180deg,#080812_0%,#111022_52%,#080812_100%)]" />
      <div className="pointer-events-none absolute left-1/2 top-[-220px] h-[440px] w-[min(760px,90vw)] -translate-x-1/2 rounded-full bg-[linear-gradient(135deg,#6D28D9_0%,#EC4899_45%,#F97316_100%)] opacity-30 blur-3xl" />
      <nav className="relative z-10 mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 py-5 sm:px-6 lg:px-8">
        <Link href="/" aria-label="Sellora home" className="min-w-0"><BrandLockup /></Link>
        <Link href="/login" className="shrink-0 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm font-bold text-white backdrop-blur transition hover:bg-white/15">Увійти</Link>
      </nav>
      <div className="relative mx-auto grid min-h-[78vh] w-full max-w-7xl content-center gap-12 px-4 pb-10 pt-4 sm:px-6 lg:grid-cols-[0.98fr_1.02fr] lg:items-center lg:px-8 lg:pb-16 lg:pt-8">
        <div className="min-w-0">
          <p className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-4 py-2 text-sm font-semibold text-pink-100"><Sparkles className="h-4 w-4" /> CRM для Instagram-магазинів</p>
          <h1 className="mt-6 max-w-4xl text-balance text-4xl font-black leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">Операційна система для продажів з Instagram — без хаосу в таблицях</h1>
          <p className="mt-5 max-w-2xl text-base leading-8 text-slate-300 sm:text-lg">Sellora обʼєднує Direct-ліди, клієнтів, замовлення, склад, відправлення, рекламу та прибуток у premium CRM, яка зручно працює на десктопі й мобільному.</p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link href="/login" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl bg-white px-6 py-3 font-black text-slate-950 shadow-2xl shadow-pink-500/20 transition hover:-translate-y-0.5">Увійти в кабінет <ArrowRight className="h-4 w-4" /></Link>
            <a href="#features" className="inline-flex min-h-12 items-center justify-center rounded-2xl border border-white/15 bg-white/10 px-6 py-3 font-bold text-white backdrop-blur transition hover:bg-white/15">Дивитись можливості</a>
          </div>
          <LandingFlow />
        </div>
        <HeroPreview />
      </div>
    </section>
  );
}

function LandingFlow() {
  return <div className="mt-8 flex max-w-3xl flex-wrap gap-2 text-xs text-slate-200 sm:text-sm">{workflow.map((item, index) => <span key={item} className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-3 py-2 font-semibold">{item}{index < workflow.length - 1 ? <span className="text-orange-300">→</span> : null}</span>)}</div>;
}

function HeroPreview() {
  return (
    <div className="relative min-w-0 rounded-[2rem] border border-white/10 bg-white/[0.06] p-3 shadow-2xl shadow-purple-950/40 backdrop-blur sm:p-5">
      <div className="rounded-[1.5rem] border border-white/10 bg-[#0F1020]/95 p-4 sm:p-5">
        <div className="flex items-center justify-between gap-3"><div className="flex items-center gap-3"><BrandIcon className="h-10 w-10" /><div><p className="text-sm font-black">Sellora dashboard</p><p className="text-xs text-slate-400">Today’s operating view</p></div></div><span className="rounded-full bg-emerald-400/10 px-3 py-1 text-xs font-bold text-emerald-200">Live</span></div>
        <div className="mt-5 grid gap-3 sm:grid-cols-3"><PreviewCard label="Revenue" value="₴24.8k" /><PreviewCard label="ROAS" value="4.7x" /><PreviewCard label="Orders" value="312" /></div>
        <div className="mt-4 grid gap-3 lg:grid-cols-[1.35fr_.65fr]"><div className="h-48 rounded-3xl bg-[radial-gradient(circle_at_20%_20%,rgba(236,72,153,.40),transparent_35%),linear-gradient(135deg,rgba(109,40,217,.55),rgba(249,115,22,.22))] p-4"><div className="h-full rounded-2xl border border-white/10 bg-black/20" /></div><div className="grid gap-3"><PreviewCard label="Shipments" value="8 active" /><PreviewCard label="Low stock" value="5 SKUs" /></div></div>
      </div>
    </div>
  );
}

function PreviewCard({ label, value }: { label: string; value: string }) { return <div className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.07] p-4"><p className="truncate text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">{label}</p><p className="mt-2 truncate text-2xl font-black text-white">{value}</p></div>; }

function LandingFeatureCard({ title, description }: { title: string; description: string }) {
  return <article className="min-w-0 rounded-3xl border border-white/10 bg-white/[0.045] p-5 shadow-2xl shadow-black/15 transition hover:-translate-y-1 hover:bg-white/[0.07] sm:p-6"><div className="mb-5 grid h-11 w-11 place-items-center rounded-2xl bg-[linear-gradient(135deg,#6D28D9_0%,#EC4899_55%,#F97316_100%)]"><CheckCircle2 className="h-5 w-5 text-white" /></div><h3 className="text-lg font-black text-white">{title}</h3><p className="mt-2 text-sm leading-6 text-slate-300">{description}</p></article>;
}

export function LandingDashboardPreview() {
  return (
    <section className="relative bg-[#080812] px-4 py-16 text-white sm:px-6 lg:px-8">
      <div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
        <div className="min-w-0"><p className="text-sm font-bold uppercase tracking-[0.28em] text-orange-300">Workflow clarity</p><h2 className="mt-3 max-w-2xl text-3xl font-black leading-tight sm:text-4xl">Вся операційка магазину — в одному охайному кабінеті</h2><p className="mt-4 max-w-2xl text-base leading-8 text-slate-300">Історичні імпорти, ручні продажі, складські резерви та рекламні метрики працюють разом, не ламаючи мобільну верстку.</p></div>
        <div className="grid gap-3 sm:grid-cols-3">{benefits.map(([title, description]) => <div key={title} className="rounded-3xl border border-white/10 bg-white/[0.055] p-5"><h3 className="font-black">{title}</h3><p className="mt-2 text-sm leading-6 text-slate-300">{description}</p></div>)}</div>
      </div>
    </section>
  );
}

export function LandingPage() {
  return <main className="min-w-0 overflow-x-hidden bg-[#080812]"><LandingHero /><section id="features" className="bg-[#080812] px-4 py-16 sm:px-6 lg:px-8"><div className="mx-auto max-w-7xl"><div className="mb-8 max-w-3xl"><p className="text-sm font-bold uppercase tracking-[0.28em] text-pink-300">Можливості</p><h2 className="mt-3 text-3xl font-black leading-tight text-white sm:text-4xl">Побудовано для Instagram-продажів</h2><p className="mt-3 text-slate-300">Без перевантаження: тільки ключові процеси, які команда використовує щодня.</p></div><div className="grid min-w-0 gap-4 md:grid-cols-2 lg:grid-cols-3">{features.map(([title, description]) => <LandingFeatureCard key={title} title={title} description={description} />)}</div></div></section><LandingDashboardPreview /><section className="bg-[#080812] px-4 pb-16 sm:px-6 lg:px-8"><div className="mx-auto max-w-5xl rounded-[2rem] border border-white/10 bg-white/[0.06] p-6 text-center shadow-2xl shadow-purple-950/20 sm:p-10"><h2 className="text-2xl font-black text-white sm:text-4xl">Готові навести порядок у продажах?</h2><p className="mx-auto mt-3 max-w-2xl text-slate-300">Почніть із кабінету Sellora та перевірте ключові сценарії staging без зміни deployment architecture.</p><Link href="/login" className="mt-6 inline-flex min-h-12 items-center justify-center rounded-2xl bg-white px-6 py-3 font-black text-slate-950">Увійти в Sellora</Link></div></section><footer className="border-t border-white/10 bg-[#080812] px-5 py-8 text-center text-sm text-slate-400">© 2026 Sellora. CRM для Instagram-магазинів.</footer></main>;
}
