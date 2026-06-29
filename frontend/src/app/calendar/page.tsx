"use client";

import { useI18n } from "@/i18n/provider";

export default function Page() {
  const { t } = useI18n();
  return <main className="min-h-screen min-w-0 overflow-x-hidden bg-[#F8F7FC] p-4 sm:p-6"><section className="mx-auto min-w-0 max-w-5xl rounded-[28px] bg-white p-8 shadow-[0_18px_45px_rgba(15,23,42,0.06)]"><p className="text-sm font-bold uppercase tracking-[0.25em] text-violet-600">Sellora</p><h1 className="mt-3 text-4xl font-black text-slate-950">{t("navigation.calendar")}</h1><p className="mt-3 max-w-2xl text-slate-600">{t("analytics.comingSoon")}</p></section></main>;
}
