import Link from "next/link";
import { BrandLockup } from "@/components/brand";

type LegalSection = {
  title: string;
  body: string[];
};

export function LegalPageShell({ title, subtitle, sections }: { title: string; subtitle: string; sections: LegalSection[] }) {
  return (
    <main className="min-h-screen bg-[#080812] px-4 py-8 text-white sm:px-6 lg:px-8">
      <div className="mx-auto max-w-4xl">
        <nav className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <Link href="/" aria-label="Sellora" className="w-fit">
            <BrandLockup />
          </Link>
          <div className="flex flex-wrap gap-2 text-sm font-bold text-slate-200">
            <Link className="rounded-full border border-white/10 bg-white/10 px-4 py-2 transition hover:bg-white/15" href="/legal/privacy">Політика / Privacy</Link>
            <Link className="rounded-full border border-white/10 bg-white/10 px-4 py-2 transition hover:bg-white/15" href="/legal/terms">Умови / Terms</Link>
            <Link className="rounded-full border border-white/10 bg-white/10 px-4 py-2 transition hover:bg-white/15" href="/legal/data-deletion">Видалення / Deletion</Link>
          </div>
        </nav>

        <section className="mt-10 rounded-[2rem] border border-white/10 bg-white/[0.06] p-6 shadow-2xl shadow-purple-950/20 sm:p-10">
          <p className="text-sm font-bold uppercase tracking-[0.28em] text-pink-200">Sellora legal draft</p>
          <h1 className="mt-4 text-3xl font-black tracking-tight sm:text-5xl">{title}</h1>
          <p className="mt-4 max-w-3xl text-base leading-8 text-slate-300">{subtitle}</p>
          <div className="mt-6 rounded-2xl border border-amber-300/20 bg-amber-300/10 p-4 text-sm font-semibold leading-6 text-amber-100">
            Ці сторінки є MVP-чернетками для підготовки продукту. Вони мають бути перевірені кваліфікованим юристом перед production launch, активацією оплат або поданням на Meta App Review.
            <br />
            These pages are MVP drafts for product readiness and require qualified legal review before production launch, payment activation, or Meta App Review submission.
          </div>
        </section>

        <div className="mt-6 grid gap-4">
          {sections.map((section) => (
            <section key={section.title} className="rounded-3xl border border-white/10 bg-white/[0.045] p-6 sm:p-8">
              <h2 className="text-2xl font-black">{section.title}</h2>
              <div className="mt-4 grid gap-3 text-sm leading-7 text-slate-300 sm:text-base">
                {section.body.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
              </div>
            </section>
          ))}
        </div>

        <footer className="py-8 text-center text-sm text-slate-500">
          <Link className="font-bold text-slate-300 hover:text-white" href="/">← Повернутися до Sellora / Back to Sellora</Link>
        </footer>
      </div>
    </main>
  );
}
