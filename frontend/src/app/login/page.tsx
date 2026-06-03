"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { BrandLogo } from "@/components/brand";
import { useAuth } from "@/hooks/use-auth";

export default function LoginPage() {
  const router = useRouter();
  const { status, login, error: authError } = useAuth();
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
      setError(exc instanceof Error ? exc.message : "Unable to sign in");
    } finally {
      setIsSubmitting(false);
    }
  }

  return <main className="relative grid min-h-screen place-items-center overflow-hidden bg-[#080812] p-5 text-white"><div className="absolute left-1/2 top-[-220px] h-[520px] w-[720px] -translate-x-1/2 rounded-full bg-[linear-gradient(135deg,#6D28D9_0%,#EC4899_45%,#F97316_75%,#FACC15_100%)] opacity-35 blur-3xl" /><Link href="/" className="absolute left-5 top-5 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-bold text-white backdrop-blur">← Landing</Link><form className="relative z-10 w-full max-w-md rounded-[28px] border border-white/10 bg-white p-7 text-slate-950 shadow-2xl shadow-pink-950/30 sm:p-8" onSubmit={submit}><div className="mb-7 flex justify-center"><BrandLogo className="h-auto w-56 max-w-full" /></div><p className="text-sm font-bold uppercase tracking-[0.25em] text-violet-600">Secure workspace login</p><h1 className="mt-3 text-3xl font-black">Увійти в кабінет</h1><p className="mt-2 text-sm leading-6 text-slate-600">Після входу Sellora автоматично завантажить /auth/me, вибере workspace і відкриє dashboard.</p><label className="mt-6 grid gap-2 text-sm font-bold text-slate-700">Email<input className="min-h-12 rounded-2xl border border-slate-200 bg-slate-50 px-4 outline-none transition focus:border-violet-300 focus:ring-4 focus:ring-violet-100" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label><label className="mt-4 grid gap-2 text-sm font-bold text-slate-700">Password<input className="min-h-12 rounded-2xl border border-slate-200 bg-slate-50 px-4 outline-none transition focus:border-violet-300 focus:ring-4 focus:ring-violet-100" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>{error || authError ? <p className="mt-4 rounded-2xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error ?? authError}</p> : null}<button className="mt-6 min-h-12 w-full rounded-2xl bg-[linear-gradient(135deg,#6D28D9_0%,#EC4899_45%,#F97316_75%,#FACC15_100%)] px-4 py-3 font-black text-white shadow-lg shadow-pink-500/20 transition hover:scale-[1.01] disabled:cursor-not-allowed disabled:opacity-70" type="submit" disabled={isSubmitting}>{isSubmitting ? "Signing in…" : "Увійти"}</button><p className="mt-5 text-center text-xs text-slate-500">Tokens and workspace are handled automatically and never shown in the UI.</p></form></main>;
}
