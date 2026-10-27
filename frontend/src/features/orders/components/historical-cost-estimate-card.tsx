"use client";

import { FormEvent, useEffect, useState } from "react";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import type { HistoricalCostSource, HistoricalEstimatedCostPayload, Order } from "@/types/orders";

const SOURCES: HistoricalCostSource[] = [
  "SHEET_ROW_MATCH",
  "PRICE_MEDIAN",
  "PRICE_BAND",
  "MANUAL",
];

export function HistoricalCostEstimateCard({
  order,
  currencyCode,
  canEdit,
  saving,
  error,
  onSave,
  onClear,
}: {
  order: Order;
  currencyCode: string;
  canEdit: boolean;
  saving?: boolean;
  error?: string | null;
  onSave?: (payload: HistoricalEstimatedCostPayload) => void;
  onClear?: () => void;
}) {
  const { t } = useI18n();
  const [amount, setAmount] = useState(order.estimated_product_cost ?? "");
  const [source, setSource] = useState<HistoricalCostSource>(
    order.estimated_cost_source ?? "MANUAL",
  );
  const [reference, setReference] = useState(order.estimated_cost_reference ?? "");
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    setAmount(order.estimated_product_cost ?? "");
    setSource(order.estimated_cost_source ?? "MANUAL");
    setReference(order.estimated_cost_reference ?? "");
    setValidationError(null);
  }, [order.id, order.estimated_product_cost, order.estimated_cost_source, order.estimated_cost_reference]);

  if (!order.is_historical || order.product_cost != null) return null;

  function handleSave(event: FormEvent) {
    event.preventDefault();
    const value = Number(amount);
    if (!Number.isFinite(value) || value <= 0 || value > 9999999999.99 || Math.abs(value * 100 - Math.round(value * 100)) > 1e-7) {
      setValidationError(t("orders.historicalEstimate.validationAmount"));
      return;
    }
    if (source === "SHEET_ROW_MATCH" && !reference.trim()) {
      setValidationError(t("orders.historicalEstimate.validationReference"));
      return;
    }
    setValidationError(null);
    onSave?.({ amount: value, source, reference: reference.trim() || null });
  }

  const hasEstimate = order.estimated_product_cost !== null;
  return (
    <section className="min-w-0 rounded-xl border border-border-subtle bg-surface-1 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">{t("orders.historicalEstimate.title")}</h3>
        <span className="rounded-full border border-amber-400/40 px-2 py-1 text-xs font-semibold text-amber-700 dark:text-amber-200">
          {t("orders.historicalEstimate.notConfirmed")}
        </span>
      </div>
      <p className="mt-2 text-sm text-text-secondary">{t("orders.historicalEstimate.help")}</p>
      {hasEstimate ? (
        <div className="mt-3 grid gap-1 rounded-lg bg-surface-2 p-3 text-sm">
          <strong className="text-base text-text-primary">{formatMoney(order.estimated_product_cost, currencyCode)}</strong>
          {order.estimated_cost_source && (
            <span>{t("orders.historicalEstimate.source")}: {t("orders.historicalEstimate.sources." + order.estimated_cost_source)}</span>
          )}
          {order.estimated_cost_confidence && (
            <span>{t("orders.historicalEstimate.confidence")}: {t("orders.historicalEstimate.confidences." + order.estimated_cost_confidence)}</span>
          )}
          {order.estimated_cost_reference && (
            <span className="break-all">{t("orders.historicalEstimate.reference")}: {order.estimated_cost_reference}</span>
          )}
        </div>
      ) : (
        <p className="mt-3 text-sm text-text-muted">{t("orders.historicalEstimate.empty")}</p>
      )}
      {canEdit && onSave && (
        <form className="mt-4 grid gap-3" onSubmit={handleSave}>
          <label className="grid gap-1 text-sm font-semibold text-text-primary">
            {t("orders.historicalEstimate.amount")}
            <input
              type="number"
              inputMode="decimal"
              min="0.01"
              step="0.01"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              disabled={saving}
              className="min-h-11 w-full min-w-0 rounded-lg border border-input-border bg-input-background px-3 py-2 font-normal"
            />
          </label>
          <label className="grid gap-1 text-sm font-semibold text-text-primary">
            {t("orders.historicalEstimate.source")}
            <select
              value={source}
              onChange={(event) => setSource(event.target.value as HistoricalCostSource)}
              disabled={saving}
              className="min-h-11 w-full min-w-0 rounded-lg border border-input-border bg-input-background px-3 py-2 font-normal"
            >
              {SOURCES.map((candidate) => (
                <option key={candidate} value={candidate}>
                  {t("orders.historicalEstimate.sources." + candidate)}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-1 text-sm font-semibold text-text-primary">
            {t("orders.historicalEstimate.reference")}
            <input
              type="text"
              maxLength={512}
              value={reference}
              onChange={(event) => setReference(event.target.value)}
              disabled={saving}
              placeholder={t("orders.historicalEstimate.referencePlaceholder")}
              className="min-h-11 w-full min-w-0 rounded-lg border border-input-border bg-input-background px-3 py-2 font-normal"
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              type="submit"
              disabled={saving}
              className="min-h-11 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-50"
            >
              {saving ? t("common.saving") : t("orders.historicalEstimate.save")}
            </button>
            {hasEstimate && onClear && (
              <button
                type="button"
                disabled={saving}
                onClick={onClear}
                className="min-h-11 rounded-lg border border-border-subtle px-4 py-2 text-sm font-semibold text-text-primary disabled:opacity-50"
              >
                {t("orders.historicalEstimate.clear")}
              </button>
            )}
          </div>
        </form>
      )}
      {(validationError || error) && (
        <p role="alert" className="mt-3 text-sm font-semibold text-danger">{validationError || error}</p>
      )}
      <p className="mt-3 text-xs text-text-muted">{t("orders.historicalEstimate.exclusion")}</p>
    </section>
  );
}
