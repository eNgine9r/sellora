"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, LockKeyhole } from "lucide-react";
import { BrandLockup } from "@/components/brand";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";

export default function LoginPage() {
  const router = useRouter();
  const { status, login, error: authError } = useAuth();
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { if (status === "authenticated") router.replace("/dashboard"); }, [router, status]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : t("auth.error"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="relative grid min-h-screen min-w-0 place-items-center overflow-hidden bg-[#080812] px-4 py-8 text-white sm:px-6">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_8%,rgba(109,40,217,.38),transparent_34%),radial-gradient(circle_at_84%_18%,rgba(236,72,153,.24),transparent_32%),linear-gradient(180deg,#080812_0%,#111022_56%,#080812_100%)]" />
      <Link href="/" className="absolute left-4 top-4 z-10 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-sm font-bold text-white backdrop-blur transition hover:bg-white/15 sm:left-6 sm:top-6"><ArrowLeft className="h-4 w-4" />{t("landing.secondaryCta")}</Link>
      <section className="relative z-10 grid w-full max-w-5xl overflow-hidden rounded-[2rem] border border-white/10 bg-white/[0.06] shadow-2xl shadow-purple-950/30 backdrop-blur lg:grid-cols-[0.9fr_1.1fr]">
        <div className="hidden min-w-0 border-r border-white/10 p-8 lg:grid lg:content-between">
          <BrandLockup />
          <div className="mt-16">
            <p className="inline-flex rounded-full border border-white/10 bg-white/10 px-4 py-2 text-sm font-bold text-pink-100">{t("auth.loginTitle")}</p>
            <h1 className="mt-5 text-4xl font-black leading-tight">{t("landing.headline")}</h1>
            <p className="mt-4 max-w-md leading-7 text-slate-300">{t("auth.helper")}</p>
          </div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Auth · RBAC · Workspace</p>
        </div>
        <form className="min-w-0 bg-white p-6 text-slate-950 sm:p-8 lg:p-10" onSubmit={submit} noValidate>
          <div className="mb-8 lg:hidden"><BrandLockup textClassName="text-slate-950" /></div>
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-violet-50 text-violet-700"><LockKeyhole className="h-6 w-6" /></div>
          <p className="mt-6 text-sm font-bold uppercase tracking-[0.22em] text-violet-600">{t("auth.loginTitle")}</p>
          <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">{t("auth.loginTitle")}</h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">{t("auth.helper")}</p>
          <label className="mt-7 grid gap-2 text-sm font-bold text-slate-700">{t("auth.email")}<input className="min-h-12 w-full min-w-0 rounded-2xl border border-slate-200 bg-slate-50 px-4 outline-none transition focus:border-violet-300 focus:ring-4 focus:ring-violet-100" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label className="mt-4 grid gap-2 text-sm font-bold text-slate-700">{t("auth.password")}<input className="min-h-12 w-full min-w-0 rounded-2xl border border-slate-200 bg-slate-50 px-4 outline-none transition focus:border-violet-300 focus:ring-4 focus:ring-violet-100" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          {error || authError ? <p className="mt-4 rounded-2xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error ?? authError}</p> : null}
          <button className="mt-6 min-h-12 w-full rounded-2xl bg-[linear-gradient(135deg,#6D28D9_0%,#EC4899_55%,#F97316_100%)] px-4 py-3 font-black text-white shadow-lg shadow-pink-500/20 transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-70" type="submit" disabled={isSubmitting}>{isSubmitting ? t("auth.loading") : t("auth.login")}</button>
          <p className="mt-5 text-center text-xs text-slate-500">{t("language.description")}</p>
        </form>
      </section>
    </main>
  );
}
