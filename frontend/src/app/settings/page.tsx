const cards = [
  {
    title: "Import Center",
    description: "Upload Excel or CSV files, preview rows, validate mappings, and import historical data.",
    href: "/settings/import",
    action: "Open Import Center",
    badge: "Data tools",
  },
  {
    title: "Integrations",
    description: "Connect delivery and external services such as Nova Poshta.",
    href: "/settings/integrations",
    action: "Open Integrations",
    badge: "Connections",
  },
  {
    title: "Nova Poshta",
    description: "Configure Nova Poshta credentials, sender settings, cities, warehouses, and TTN creation.",
    href: "/settings/integrations",
    action: "Configure Nova Poshta",
    badge: "Delivery",
  },
];

export default function Page() {
  return (
    <main className="min-h-screen bg-[#F8F7FC] p-4 text-slate-950 sm:p-6">
      <div className="mx-auto grid max-w-6xl gap-6">
        <section className="rounded-[28px] bg-white p-6 shadow-[0_18px_45px_rgba(15,23,42,0.06)] sm:p-8">
          <p className="text-sm font-bold uppercase tracking-[0.25em] text-violet-600">Sellora</p>
          <h1 className="mt-3 text-4xl font-black text-slate-950">Settings</h1>
          <p className="mt-3 max-w-2xl text-slate-600">Manage workspace tools, import workflows, and external service integrations from one place.</p>
        </section>
        <section className="grid gap-4 md:grid-cols-3">
          {cards.map((card) => (
            <article key={card.title} className="flex min-h-64 flex-col justify-between rounded-[24px] bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.06)]">
              <div className="grid gap-3">
                <span className="w-fit rounded-full bg-violet-50 px-3 py-1 text-xs font-black uppercase tracking-[0.18em] text-violet-700">{card.badge}</span>
                <h2 className="text-2xl font-black text-slate-950">{card.title}</h2>
                <p className="text-sm leading-6 text-slate-600">{card.description}</p>
              </div>
              <a className="mt-6 inline-flex min-h-11 items-center justify-center rounded-2xl bg-violet-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-violet-700" href={card.href}>{card.action}</a>
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}
