"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";

export default function Home() {
  const router = useRouter();
  const { status } = useAuth();

  useEffect(() => {
    if (status === "authenticated") router.replace("/overview");
    if (status === "unauthenticated") router.replace("/login");
  }, [router, status]);

  return <main className="grid min-h-screen place-items-center bg-slate-950 text-white"><p className="text-sm text-slate-300">Opening Sellora…</p></main>;
}
