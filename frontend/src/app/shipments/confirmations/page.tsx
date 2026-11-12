"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { WorkspaceHeader, WorkspacePage } from "@/components/crm-workspace";
import { NovaPoshtaExternalInbox } from "@/features/shipments/components/nova-poshta-external-inbox";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";

export default function ShipmentSaleConfirmationsPage() {
  const { locale } = useI18n();
  const { currentWorkspace, currentWorkspaceId, status } = useAuth();
  const isEnglish = locale === "en";
  const title = isEnglish ? "Sale confirmations" : "Підтвердження продажів";
  const allowed = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";

  return <WorkspacePage>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <WorkspaceHeader
        title={title}
        description={isEnglish
          ? "One shipment at a time. Check the actual sale and confirm."
          : "Одне відправлення за раз: перевірте продаж і підтвердьте."}
      />
      <Link href="/shipments" className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-border-subtle bg-surface px-4 text-sm font-semibold text-text-primary hover:bg-surface-hover">
        <ArrowLeft aria-hidden="true" className="h-4 w-4" />
        {isEnglish ? "All shipments" : "Усі доставки"}
      </Link>
    </div>
    {status === "authenticated" && currentWorkspaceId && allowed
      ? <NovaPoshtaExternalInbox key={currentWorkspaceId} workspaceId={currentWorkspaceId} role={currentWorkspace?.role} mode="full" />
      : status === "authenticated" && !allowed
        ? <p role="alert" className="rounded-xl border border-border-subtle bg-surface p-4 text-sm text-text-secondary">
          {isEnglish ? "Only owners and managers can confirm sales." : "Підтверджувати продажі можуть власник і менеджер."}
        </p>
        : <p className="rounded-xl border border-border-subtle bg-surface p-4 text-sm text-text-secondary">
          {isEnglish ? "Loading workspace…" : "Завантажуємо робочий простір…"}
        </p>}
  </WorkspacePage>;
}
