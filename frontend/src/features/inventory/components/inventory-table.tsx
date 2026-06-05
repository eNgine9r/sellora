"use client";

import { useI18n } from "@/i18n/provider";
import { statusBadgeClass } from "@/lib/status-styles";
import { Inventory, ProductVariant } from "@/types/products";

function variantLabel(item: Inventory, variant?: ProductVariant) { return variant?.sku ?? `Variant ${item.product_variant_id.slice(0, 8)}…`; }

export function InventoryTable({ inventory, variants, onEdit }: { inventory: Inventory[]; variants: ProductVariant[]; onEdit?: (inventory: Inventory) => void }) {
  const variantById = new Map(variants.map((variant) => [variant.id, variant]));
  const { t } = useI18n();
  return (
    <div className="w-full min-w-0 max-w-full rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="sellora-scrollbar hidden max-w-full overflow-x-auto lg:block">
        <table className="w-full min-w-[760px] divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500"><tr><th className="px-4 py-3">{t("tables.variantSku")}</th><th className="px-4 py-3">{t("tables.stock")}</th><th className="px-4 py-3">{t("tables.reserved")}</th><th className="px-4 py-3">{t("tables.incoming")}</th><th className="px-4 py-3">{t("tables.minimum")}</th><th className="px-4 py-3">{t("tables.status")}</th><th className="px-4 py-3">{t("tables.actions")}</th></tr></thead>
          <tbody className="divide-y divide-slate-100">{inventory.map((item) => { const variant = variantById.get(item.product_variant_id); const label = variantLabel(item, variant); return <tr key={item.id} className="hover:bg-slate-50"><td className="max-w-[220px] truncate px-4 py-3 font-medium text-slate-900">{label}</td><td className="px-4 py-3">{item.stock_quantity}</td><td className="px-4 py-3">{item.reserved_quantity}</td><td className="px-4 py-3">{item.incoming_quantity}</td><td className="px-4 py-3">{item.minimum_quantity}</td><td className="px-4 py-3">{item.is_low_stock ? <span className={statusBadgeClass("danger")}>{t("inventory.lowStock")}</span> : <span className={statusBadgeClass("success")}>{t("inventory.healthy")}</span>}</td><td className="px-4 py-3">{onEdit ? <button aria-label={`${t("inventory.editThresholds")} ${label}`} className="rounded-lg border border-slate-300 px-3 py-2 font-semibold" onClick={() => onEdit(item)}>{t("inventory.editThresholds")}</button> : <span className="text-slate-400">{t("common.readOnly")}</span>}</td></tr>; })}{inventory.length === 0 ? <tr><td className="px-4 py-8 text-center text-slate-500" colSpan={7}>{t("inventory.empty")}</td></tr> : null}</tbody>
        </table>
      </div>
      <div className="grid gap-3 lg:hidden">
        {inventory.map((item) => { const variant = variantById.get(item.product_variant_id); const label = variantLabel(item, variant); return <article className="min-w-0 rounded-2xl border border-slate-200 p-4" key={item.id}><div className="flex min-w-0 items-start justify-between gap-3"><div className="min-w-0"><p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">{t("tables.variantSku")}</p><h3 className="truncate text-lg font-black text-slate-950">{label}</h3></div>{item.is_low_stock ? <span className={`${statusBadgeClass("danger")} shrink-0`}>{t("inventory.lowStock")}</span> : <span className={`${statusBadgeClass("success")} shrink-0`}>{t("inventory.healthy")}</span>}</div><div className="mt-4 grid grid-cols-2 gap-2 text-sm text-slate-600"><span>{t("tables.stock")}: <strong>{item.stock_quantity}</strong></span><span>{t("tables.reserved")}: <strong>{item.reserved_quantity}</strong></span><span>{t("tables.incoming")}: <strong>{item.incoming_quantity}</strong></span><span>{t("tables.minimum")}: <strong>{item.minimum_quantity}</strong></span></div>{onEdit ? <button aria-label={`${t("inventory.editThresholds")} ${label}`} className="mt-4 min-h-11 w-full rounded-xl border border-slate-300 px-4 py-3 font-bold" onClick={() => onEdit(item)}>{t("inventory.editThresholds")}</button> : <p className="mt-4 text-sm text-slate-400">{t("common.readOnly")}</p>}</article>; })}
        {inventory.length === 0 ? <p className="p-6 text-center text-slate-500">{t("inventory.empty")}</p> : null}
      </div>
    </div>
  );
}
// Localization regression compatibility markers: Edit thresholds.
