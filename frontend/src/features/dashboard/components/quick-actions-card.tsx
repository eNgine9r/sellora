import Link from "next/link";

const actions = [["New order", "/orders"], ["Add product", "/products"], ["Create shipment", "/shipments"], ["Import data", "/settings/import"]];
export function QuickActionsCard() { return <section className="rounded-[20px] border border-slate-100 bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.06)]"><h2 className="text-lg font-black">Quick actions</h2><div className="mt-4 grid gap-3 sm:grid-cols-2">{actions.map(([label, href]) => <Link key={label} href={href} className="rounded-2xl bg-violet-50 px-4 py-3 text-sm font-bold text-violet-700 transition hover:bg-violet-100">{label}</Link>)}</div></section>; }
