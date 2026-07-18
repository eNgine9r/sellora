"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Button, WorkspaceHeader, WorkspacePage } from "@/components/crm-workspace";
import { LoadingSkeleton } from "@/components/ui/states";

export default function InstagramCallbackPage() {
  const params = useSearchParams();
  const [seconds, setSeconds] = useState(3);
  const status = useMemo(() => params.get("status") ?? (params.get("error") ? "failed" : "processing"), [params]);
  useEffect(() => { const id = window.setInterval(() => setSeconds((value) => Math.max(0, value - 1)), 1000); return () => window.clearInterval(id); }, []);
  useEffect(() => { if (seconds === 0) window.location.assign("/settings/integrations/instagram"); }, [seconds]);
  return <WorkspacePage><WorkspaceHeader eyebrow="Meta Instagram" title="Повернення з Instagram Login" description="Sellora перевіряє результат підключення без показу token або authorization code у frontend." />{status === "processing" ? <LoadingSkeleton /> : null}<section className="rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-4 shadow-[var(--shadow-card)]"><h2 className="font-black">{status === "connected" ? "Instagram підключено" : status === "permission_missing" ? "Потрібні дозволи Meta" : "Перевірте статус підключення"}</h2><p className="mt-2 text-sm text-text-secondary">Безпечне перенаправлення до налаштувань через {seconds} с. Якщо редірект не спрацює, натисніть кнопку нижче.</p><Button className="mt-4" onClick={() => window.location.assign("/settings/integrations/instagram")}>Відкрити налаштування Instagram</Button></section></WorkspacePage>;
}
