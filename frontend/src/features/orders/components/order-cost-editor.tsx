"use client";

import { FormEvent, useEffect, useState } from "react";
import { useI18n } from "@/i18n/provider";
import { isNonNegativeAmount } from "@/features/orders/lib/fulfillment-amounts";
import type { Order, OrderProductCostsPayload } from "@/types/orders";

function costValues(order: Order): Record<string, string> {
  return Object.fromEntries(order.items.map((item) => [item.id,
    (item.cost_confirmed ?? Number(item.unit_cost) > 0) ? String(item.unit_cost) : "",
  ]));
}

export function OrderCostEditor({ order, onSave, saving, error }: {
  order: Order;
  onSave: (payload: OrderProductCostsPayload) => Promise<void>;
  saving?: boolean;
  error?: string | null;
}) {
  const { t } = useI18n();
  const [editing, setEditing] = useState(false);
  const [values, setValues] = useState(() => costValues(order));
  const [invalid, setInvalid] = useState(false);

  useEffect(() => {
    setValues(costValues(order));
    setEditing(false);
    setInvalid(false);
  }, [order]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const bad = order.items.some((item) => {
      const text = (values[item.id] ?? "").trim();
      const n = Number(text);
      return text !== "" && (!isNonNegativeAmount(text) || n > 9999999999.99 || Math.abs(n * 100 - Math.round(n * 100)) > 1e-7);
    });
    if (bad) { setInvalid(true); return; }
    setInvalid(false);
    try {
      await onSave({ items: order.items.map((item) => ({ item_id: item.id,
        unit_cost: (values[item.id] ?? "").trim() === "" ? null : Number(values[item.id]),
      })) });
      setEditing(false);
    } catch {
      // The page displays the request error and keeps the user's inputs.
    }
  }

  if (!order.items.length) return null;
  return <section className="grid gap-3 rounded-xl border border-border-subtle bg-surface-1 p-4">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h3 className="font-semibold">{t("orders.costCorrection.title")}</h3>
      {!editing ? <button type="button" className="min-h-10 rounded-lg border border-border-subtle px-3 py-2 text-sm font-bold" onClick={() => { setValues(costValues(order)); setEditing(true); }}>{t("orders.costCorrection.edit")}</button> : null}
    </div>
    <p className="text-sm text-text-secondary">{t("orders.costCorrection.help")}</p>
    {editing ? <form className="grid gap-3" onSubmit={save}>
      {order.items.map((item) => <label key={item.id} className="grid gap-1 text-sm font-semibold">
        {item.product_name} · {item.sku} · {item.quantity} ×
        <input type="number" inputMode="decimal" min="0" step="0.01" value={values[item.id] ?? ""}
          placeholder={t("orders.unknownAmount")} onChange={(event) => setValues((current) => ({ ...current, [item.id]: event.target.value }))}
          className="min-h-11 rounded-xl border border-input-border bg-input-background px-3 py-2 text-text-primary" />
      </label>)}
      {invalid ? <p role="alert" className="text-sm text-danger">{t("orders.costCorrection.invalid")}</p> : null}
      {error ? <p role="alert" className="text-sm text-danger">{error}</p> : null}
      <div className="flex flex-wrap gap-2">
        <button type="submit" disabled={saving} className="min-h-11 rounded-xl bg-primary px-4 py-2 font-bold text-primary-foreground disabled:opacity-50">{saving ? t("common.loading") : t("orders.costCorrection.save")}</button>
        <button type="button" disabled={saving} className="min-h-11 rounded-xl border border-border-subtle px-4 py-2 font-bold" onClick={() => setEditing(false)}>{t("actions.cancel")}</button>
      </div>
    </form> : null}
  </section>;
}
