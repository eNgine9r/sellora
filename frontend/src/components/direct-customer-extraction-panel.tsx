"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BadgeCheck, BrainCircuit, CheckCircle2, RefreshCw, ShieldAlert, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

import {
  applyDirectCustomerExtraction,
  extractDirectCustomerData,
  fetchDirectCustomerExtraction,
} from "@/services/direct";
import { DirectCustomerExtractionData } from "@/types/direct";

const FIELD_LABELS: Record<string, string> = {
  name: "ПІБ",
  phone: "телефон",
  city: "місто",
  region: "область",
  delivery_address: "адресу доставки",
  recipient_name: "ПІБ",
  warehouse_number: "відділення",
};

const SAFE_ERROR_LABELS: Record<string, string> = {
  AI_RATE_LIMITED: "OpenAI тимчасово обмежив частоту запитів. Sellora повторить розпізнавання автоматично.",
  AI_BILLING_QUOTA_EXCEEDED: "Для OpenAI API недостатньо доступного балансу або ліміту проєкту.",
  AI_PROVIDER_CREDENTIAL_INVALID: "OpenAI API key недійсний. Перевірте backend secret AI_API_KEY.",
  AI_PROVIDER_FORBIDDEN: "API key не має дозволу Model capabilities: Write.",
  AI_PROVIDER_UNAVAILABLE: "OpenAI тимчасово недоступний. Дані клієнта не змінено.",
  AI_REQUEST_TIMEOUT: "OpenAI не відповів вчасно. Sellora повторить спробу безпечно.",
  AI_INVALID_STRUCTURED_OUTPUT: "AI не зміг сформувати надійні структуровані дані.",
};

function confidenceLabel(value: number) {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
}

function fieldRows(data: DirectCustomerExtractionData) {
  return [
    { key: "name", label: "ПІБ", value: data.recipient_name, confidence: data.recipient_name_confidence },
    { key: "phone", label: "Телефон", value: data.phone, confidence: data.phone_confidence },
    { key: "city", label: "Місто", value: data.city, confidence: data.city_confidence, verified: data.city_verified },
    {
      key: "delivery_address",
      label: data.delivery_point_type === "POSTOMAT" ? "Поштомат" : "Відділення",
      value: data.warehouse_text ?? (data.warehouse_number ? `№${data.warehouse_number}` : null),
      confidence: data.warehouse_confidence,
      verified: data.warehouse_verified,
    },
  ].filter((item) => Boolean(item.value));
}

export function DirectCustomerExtractionPanel({
  workspaceId,
  conversationId,
  canManage,
}: {
  workspaceId: string | null;
  conversationId: string | null;
  canManage: boolean;
}) {
  const queryClient = useQueryClient();
  const [target, setTarget] = useState<HTMLElement | null>(null);

  useEffect(() => {
    if (typeof document === "undefined") return;
    const resolveTarget = () => {
      const next = document.querySelector<HTMLElement>("[data-direct-customer-automation]");
      setTarget((current) => current === next ? current : next);
    };
    resolveTarget();
    const observer = new MutationObserver(resolveTarget);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [conversationId]);

  const extractionQuery = useQuery({
    queryKey: ["direct-customer-extraction", workspaceId, conversationId],
    queryFn: () => fetchDirectCustomerExtraction(conversationId!),
    enabled: Boolean(workspaceId && conversationId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "QUEUED" || status === "PROCESSING" ? 1500 : 4000;
    },
    refetchIntervalInBackground: true,
  });

  const refreshRelatedData = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["direct-customer-extraction", workspaceId, conversationId] }),
      queryClient.invalidateQueries({ queryKey: ["direct-customer-automation", workspaceId, conversationId] }),
      queryClient.invalidateQueries({ queryKey: ["direct-conversations", workspaceId] }),
      queryClient.invalidateQueries({ queryKey: ["customers", workspaceId] }),
    ]);
  };

  const extractMutation = useMutation({
    mutationFn: () => extractDirectCustomerData(conversationId!),
    onSuccess: refreshRelatedData,
  });
  const applyMutation = useMutation({
    mutationFn: (fields: string[]) => applyDirectCustomerExtraction(
      conversationId!,
      extractionQuery.data!.analysis_id,
      fields,
    ),
    onSuccess: refreshRelatedData,
  });

  if (!target || !conversationId) return null;

  const extraction = extractionQuery.data;
  const data = extraction?.data;
  const rows = data ? fieldRows(data) : [];
  const pending = extraction?.status === "QUEUED" || extraction?.status === "PROCESSING";
  const errorText = extraction?.safe_error_code
    ? SAFE_ERROR_LABELS[extraction.safe_error_code] ?? `AI-помилка: ${extraction.safe_error_code}`
    : null;

  return createPortal(
    <div className="mt-3 border-t border-border-subtle pt-3" data-direct-customer-extraction>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <BrainCircuit className="h-4 w-4 text-primary" />
            <p className="text-sm font-black">AI розпізнавання даних</p>
            {extraction?.status === "COMPLETED" && data ? (
              <span className="rounded-full bg-emerald-500/15 px-2 py-1 text-[11px] font-black text-emerald-700">
                confidence {confidenceLabel(data.overall_confidence)}
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-xs text-text-muted">
            Sellora аналізує останні повідомлення, але не створює замовлення або ТТН без менеджера.
          </p>
        </div>
        {canManage ? (
          <button
            type="button"
            onClick={() => extractMutation.mutate()}
            disabled={extractMutation.isPending || pending}
            className="inline-flex min-h-9 items-center gap-2 rounded-xl border border-border-subtle bg-surface-1 px-3 py-2 text-xs font-black text-primary disabled:cursor-not-allowed disabled:opacity-50"
          >
            {extractMutation.isPending || pending ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
            {pending ? "Розпізнаємо…" : extraction ? "Розпізнати повторно" : "Розпізнати дані"}
          </button>
        ) : null}
      </div>

      {extractionQuery.isLoading ? (
        <p className="mt-3 text-xs font-semibold text-text-muted">Перевіряємо наявні AI-дані…</p>
      ) : null}

      {errorText ? (
        <div className="mt-3 flex items-start gap-2 rounded-2xl bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-700">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{errorText}</span>
        </div>
      ) : null}

      {data && rows.length > 0 ? (
        <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          {rows.map((row) => {
            const conflict = data.conflicts.includes(row.key);
            const applied = data.applied_fields.includes(row.key);
            return (
              <div key={row.key} className={`rounded-2xl border px-3 py-2 ${conflict ? "border-amber-500/30 bg-amber-500/10" : "border-border-subtle bg-surface-1"}`}>
                <div className="flex items-center justify-between gap-2 text-[11px] font-black uppercase tracking-wide text-text-muted">
                  <span>{row.label}</span>
                  <span>{confidenceLabel(row.confidence)}</span>
                </div>
                <p className="mt-1 break-words text-sm font-black text-primary">{row.value}</p>
                <div className="mt-2 flex flex-wrap items-center gap-1 text-[11px] font-bold">
                  {row.verified ? <span className="inline-flex items-center gap-1 text-emerald-700"><BadgeCheck className="h-3.5 w-3.5" />Перевірено</span> : null}
                  {applied ? <span className="inline-flex items-center gap-1 text-emerald-700"><CheckCircle2 className="h-3.5 w-3.5" />Додано</span> : null}
                  {conflict ? <span className="text-amber-700">Відрізняється від картки</span> : null}
                </div>
                {conflict && canManage ? (
                  <button
                    type="button"
                    onClick={() => applyMutation.mutate([row.key])}
                    disabled={applyMutation.isPending}
                    className="mt-2 text-xs font-black text-primary underline-offset-4 hover:underline disabled:opacity-50"
                  >
                    Замінити {FIELD_LABELS[row.key] ?? "поле"}
                  </button>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}

      {data?.missing_fields.length ? (
        <p className="mt-3 text-xs font-semibold text-amber-700">
          AI не підтвердив: {data.missing_fields.map((field) => FIELD_LABELS[field] ?? field).join(", ")}.
        </p>
      ) : null}
      {data?.clarification_required ? (
        <p className="mt-1 text-xs font-semibold text-amber-700">Потрібно уточнити дані в клієнта перед оформленням.</p>
      ) : null}
      {extractMutation.isError || applyMutation.isError ? (
        <p className="mt-2 text-xs font-semibold text-rose-600">Операцію не виконано. Дані клієнта не змінені.</p>
      ) : null}
    </div>,
    target,
  );
}
