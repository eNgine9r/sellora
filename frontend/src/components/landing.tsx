import Link from "next/link";
import { BrandLogo } from "@/components/brand";

const features = [
  ["Leads", "Direct-звернення, джерела та статуси лідів в одному пайплайні."],
  ["Orders", "Замовлення, прибуток, статуси й історія без ручного хаосу."],
  ["Customers", "Картки клієнтів, нотатки, теги, адреси та повторні покупки."],
  ["Inventory", "Залишки, резерви, incoming та low-stock контроль."],
  ["Advertising", "Витрати, ROAS, CPA, ліди, повідомлення та продажі."],
  ["Finance", "Дохід, чистий прибуток, витрати й маржинальність."],
];

export function LandingHero() {
  return (
    <section className="relative overflow-hidden bg-[#080812] text-white">
      <div className="absolute left-1/2 top-[-180px] h-[460px] w-[720px] -translate-x-1/2 rounded-full bg-[linear-gradient(135deg,#6D28D9_0%,#EC4899_45%,#F97316_75%,#FACC15_100%)] opacity-30 blur-3xl" />
      <div className="mx-auto grid min-h-screen max-w-7xl place-items-center px-5 py-20">
        <div className="relative z-10 grid max-w-5xl gap-8 text-center">
          <div className="mx-auto rounded-3xl border border-white/10 bg-white/5 px-5 py-3 backdrop-blur"><BrandLogo className="h-auto w-52 brightness-0 invert" /></div>
          <p className="mx-auto w-fit rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-pink-100">CRM for Instagram stores</p>
          <h1 className="text-balance text-4xl font-black leading-tight tracking-tight sm:text-5xl lg:text-7xl">CRM для Instagram-магазинів, яка перетворює Direct, замовлення, склад, рекламу та прибуток в одну систему</h1>
          <p className="mx-auto max-w-3xl text-lg leading-8 text-slate-300 sm:text-xl">Керуйте лідами, клієнтами, товарами, відправленнями, рекламою та фінансами без хаосу в таблицях.</p>
          <div className="flex flex-col justify-center gap-3 sm:flex-row"><Link href="/login" className="rounded-2xl bg-white px-6 py-4 font-bold text-slate-950 shadow-2xl shadow-pink-500/20 transition hover:scale-[1.02]">Увійти в кабінет</Link><a href="#features" className="rounded-2xl border border-white/15 bg-white/10 px-6 py-4 font-bold text-white backdrop-blur transition hover:bg-white/15">Дивитись можливості</a></div>
          <LandingFlow />
        </div>
      </div>
    </section>
  );
}

function LandingFlow() {
  const items = ["Instagram Direct", "Lead", "Order", "Shipment", "Delivered", "Profit"];
  return <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-center gap-2 rounded-3xl border border-white/10 bg-white/[0.04] p-4 text-sm text-slate-200">{items.map((item, index) => <div key={item} className="flex items-center gap-2"><span className="rounded-full bg-white/10 px-4 py-2 font-semibold">{item}</span>{index < items.length - 1 ? <span className="text-orange-300">→</span> : null}</div>)}</div>;
}

export function LandingFeatureCard({ title, description }: { title: string; description: string }) {
  return <article className="rounded-3xl border border-white/10 bg-white/[0.04] p-6 shadow-2xl shadow-black/20 transition hover:-translate-y-1 hover:bg-white/[0.07]"><div className="mb-5 h-12 w-12 rounded-2xl bg-[linear-gradient(135deg,#6D28D9_0%,#EC4899_45%,#F97316_75%,#FACC15_100%)]" /><h3 className="text-xl font-bold text-white">{title}</h3><p className="mt-2 text-sm leading-6 text-slate-300">{description}</p></article>;
}

export function LandingDashboardPreview() {
  return (
    <section className="relative bg-[#080812] px-5 py-20 text-white">
      <div className="mx-auto grid max-w-7xl gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
        <div><p className="text-sm font-bold uppercase tracking-[0.3em] text-orange-300">Dashboard preview</p><h2 className="mt-3 text-3xl font-black sm:text-5xl">Вся операційка магазину — в одному екрані</h2><p className="mt-4 text-lg leading-8 text-slate-300">Бачте дохід, прибуток, ліди, ROAS, відправлення, топ-товари та активність команди без перемикання між таблицями.</p></div>
        <div className="rounded-[2rem] border border-white/10 bg-white/[0.06] p-4 shadow-2xl shadow-purple-950/40 backdrop-blur">
          <div className="grid gap-3 sm:grid-cols-3"><PreviewCard label="Дохід" value="₴24.8k" /><PreviewCard label="ROAS" value="4.7x" /><PreviewCard label="Orders" value="312" /></div>
          <div className="mt-4 h-48 rounded-3xl bg-[radial-gradient(circle_at_20%_20%,rgba(236,72,153,.45),transparent_30%),linear-gradient(135deg,rgba(109,40,217,.45),rgba(249,115,22,.25))] p-5"><div className="h-full rounded-2xl border border-white/10 bg-black/20" /></div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2"><PreviewCard label="Recent orders" value="17 new" /><PreviewCard label="Shipments" value="8 in transit" /></div>
        </div>
      </div>
    </section>
  );
}

function PreviewCard({ label, value }: { label: string; value: string }) { return <div className="rounded-2xl border border-white/10 bg-white/10 p-4"><p className="text-xs uppercase tracking-[0.2em] text-slate-300">{label}</p><p className="mt-2 text-2xl font-black">{value}</p></div>; }

export function LandingPage() {
  return <main className="bg-[#080812]"><LandingHero /><section id="features" className="bg-[#080812] px-5 py-20"><div className="mx-auto max-w-7xl"><div className="mb-10 max-w-3xl"><p className="text-sm font-bold uppercase tracking-[0.3em] text-pink-300">Можливості</p><h2 className="mt-3 text-3xl font-black text-white sm:text-5xl">Побудовано для Instagram-продажів</h2></div><div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">{features.map(([title, description]) => <LandingFeatureCard key={title} title={title} description={description} />)}</div></div></section><LandingDashboardPreview /><footer className="border-t border-white/10 bg-[#080812] px-5 py-10 text-center text-sm text-slate-400">© 2026 Sellora. CRM для Instagram-магазинів.</footer></main>;
}
