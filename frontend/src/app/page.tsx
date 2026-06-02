export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <section className="mx-auto flex min-h-screen max-w-5xl flex-col justify-center px-6 py-24">
        <p className="mb-4 text-sm font-semibold uppercase tracking-[0.3em] text-blue-300">Sellora Sprint 1.1</p>
        <h1 className="max-w-3xl text-5xl font-bold tracking-tight sm:text-7xl">SaaS CRM foundation for multi-tenant teams.</h1>
        <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
          Clean Architecture, modular monolith boundaries, authentication, RBAC, and tenant-aware infrastructure are ready for future CRM modules.
        </p>
      </section>
    </main>
  );
}
