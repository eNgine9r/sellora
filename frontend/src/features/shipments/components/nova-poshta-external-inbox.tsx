"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useI18n } from "@/i18n/provider";
import { safeApiErrorMessage } from "@/services/api";
import {
  fetchExternalNovaPoshtaDocuments,
  scanExternalNovaPoshtaDocuments,
  type ExternalNovaPoshtaScanResult,
} from "@/services/shipments";

function kyivDate(timestamp: number): string {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone: "Europe/Kyiv", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date(timestamp));
  const get = (type: string) => parts.find((item) => item.type === type)?.value ?? "";
  return [get("year"), get("month"), get("day")].join("-");
}

export function NovaPoshtaExternalInbox({
  workspaceId, role,
}: {
  workspaceId: string;
  role: string | undefined;
}) {
  const { t } = useI18n();
  const client = useQueryClient();
  const [lastScan, setLastScan] = useState<ExternalNovaPoshtaScanResult | null>(null);
  const visible = role === "OWNER" || role === "MANAGER";
  const key = ["np-external-inbox", workspaceId];
  const query = useQuery({
    queryKey: key,
    queryFn: async () => {
      const [unmatched, conflicts] = await Promise.all([
        fetchExternalNovaPoshtaDocuments(workspaceId, "UNMATCHED"),
        fetchExternalNovaPoshtaDocuments(workspaceId, "CONFLICT"),
      ]);
      return [...conflicts, ...unmatched];
    },
    enabled: visible && Boolean(workspaceId),
    staleTime: 60_000,
  });
  const scan = useMutation({
    mutationFn: () => scanExternalNovaPoshtaDocuments(
      workspaceId,
      kyivDate(Date.now() - 6 * 86_400_000),
      kyivDate(Date.now()),
    ),
    onSuccess: (result) => {
      setLastScan(result);
      void client.invalidateQueries({ queryKey: key });
    },
  });

  if (!visible) return null;
  return (
    <section className="grid min-w-0 gap-3 rounded-2xl border border-border bg-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-base font-bold text-text-primary">{t("shipments.externalInboxTitle")}</h2>
          <p className="text-sm text-text-muted">{t("shipments.externalInboxDescription")}</p>
        </div>
        {role === "OWNER" ? (
          <button
            type="button"
            disabled={scan.isPending}
            onClick={() => scan.mutate()}
            className="min-h-10 rounded-xl border border-input-border px-4 text-sm font-semibold text-text-primary disabled:opacity-50"
          >
            {scan.isPending ? t("shipments.externalScanning") : t("shipments.externalScan")}
          </button>
        ) : null}
      </div>
      {query.isLoading ? <p className="text-sm text-text-muted">{t("shipments.externalLoading")}</p> : null}
      {query.isError ? <p role="alert" className="text-sm text-red-500">{safeApiErrorMessage(query.error, t("shipments.externalLoadError"))}</p> : null}
      {scan.isError ? <p role="alert" className="text-sm text-red-500">{safeApiErrorMessage(scan.error, t("shipments.externalScanError"))}</p> : null}
      {lastScan ? (
        <p role="status" className="text-sm text-text-muted">
          {t("shipments.externalScanned")}: {lastScan.scanned} · {t("shipments.externalUnmatched")}: {lastScan.unmatched} · {t("shipments.externalConflicts")}: {lastScan.conflicts}
        </p>
      ) : null}
      {query.data && query.data.length === 0 ? (
        <p className="text-sm text-text-muted">{t("shipments.externalEmpty")}</p>
      ) : null}
      {query.data && query.data.length > 0 ? (
        <div className="grid gap-2">
          {query.data.slice(0, 12).map((item) => (
            <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border p-3">
              <span className="font-mono text-sm font-semibold text-text-primary">{item.tracking_number}</span>
              <span className="text-xs text-text-muted">{item.provider_status ?? t("shipments.externalUnknownStatus")}</span>
              <span className="text-xs font-semibold text-amber-500">
                {item.match_state === "CONFLICT" ? t("shipments.externalConflicts") : t("shipments.externalUnmatched")}
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
