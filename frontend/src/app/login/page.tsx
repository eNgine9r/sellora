"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";

export default function LoginPage() {
  const router = useRouter();
  const { status, login, error: authError } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/overview");
    }
  }, [router, status]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await login(email, password);
      router.replace("/overview");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Unable to sign in");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-slate-100 p-6 text-slate-950">
      <form className="w-full max-w-md rounded-2xl bg-white p-6 shadow-sm" onSubmit={submit}>
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Sellora staging</p>
        <h1 className="mt-2 text-3xl font-bold">Log in</h1>
        <p className="mt-1 text-sm text-slate-600">Use your Sellora email and password to open your workspace.</p>
        <label className="mt-6 grid gap-2 text-sm font-medium text-slate-700">
          Email
          <input className="rounded-md border border-slate-300 px-3 py-2" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </label>
        <label className="mt-4 grid gap-2 text-sm font-medium text-slate-700">
          Password
          <input className="rounded-md border border-slate-300 px-3 py-2" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
        </label>
        {error || authError ? <p className="mt-4 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error ?? authError}</p> : null}
        <button className="mt-6 w-full rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Signing in…" : "Log in"}
        </button>
      </form>
    </main>
  );
}
