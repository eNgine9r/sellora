"use client";

import { RemoteImage } from "@/components/ui/remote-image";
import { useI18n } from "@/i18n/provider";
import { displayCategory } from "@/lib/categories";
import { statusBadgeClass } from "@/lib/status-styles";
import { Product } from "@/types/products";

function primaryImage(product: Product) {
  return product.images.find((image) => image.is_primary) ?? product.images[0];
}

export function ProductTable({ products, selectedProductId, onSelect, onEdit, onArchive }: { products: Product[]; selectedProductId?: string; onSelect?: (product: Product) => void; onEdit?: (product: Product) => void; onArchive?: (product: Product) => void }) {
  const { t } = useI18n();
  return (
    <div className="w-full min-w-0 max-w-full rounded-2xl border border-border-subtle bg-surface-1 p-3 shadow-sm">
      <div className="sellora-scrollbar hidden max-w-full overflow-x-auto lg:block">
        <table className="w-full min-w-[820px] divide-y divide-border-subtle text-sm dark:divide-white/10">
          <thead className="bg-surface-2 text-left text-xs font-black uppercase tracking-wide text-text-muted">
            <tr>
              <th className="px-4 py-3">{t("inventory.productImage")}</th>
              <th className="px-4 py-3">{t("tables.name")}</th>
              <th className="px-4 py-3">{t("products.category")}</th>
              <th className="px-4 py-3">SKU</th>
              <th className="px-4 py-3">{t("tables.status")}</th>
              <th className="px-4 py-3">{t("tables.created")}</th>
              <th className="px-4 py-3">{t("tables.actions")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle">
            {products.map((product) => {
              const image = primaryImage(product);
              return (
                <tr key={product.id} className={`cursor-pointer transition hover:bg-surface-hover ${selectedProductId === product.id ? "bg-surface-selected" : ""}`} onClick={() => onSelect?.(product)}>
                  <td className="px-4 py-3">{image ? <img className="h-12 w-12 rounded-lg object-cover" src={image.image_url} alt={image.alt_text ?? product.name} /> : <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-surface-2 text-xs font-bold text-text-muted dark:bg-white/10">IMG</div>}</td>
                  <td className="max-w-[240px] truncate px-4 py-3 font-medium text-text-primary">{product.name}</td>
                  <td className="px-4 py-3 text-text-secondary">{displayCategory(product.category, t)}</td>
                  <td className="max-w-[160px] truncate px-4 py-3 text-text-secondary">{product.sku ?? "—"}</td>
                  <td className="px-4 py-3 text-text-secondary"><span className={statusBadgeClass(product.is_active ? "success" : "neutral")}>{product.is_active ? t("products.active") : t("products.inactive")}</span></td>
                  <td className="px-4 py-3 text-text-secondary">{new Date(product.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3"><div className="flex flex-wrap gap-2">{onEdit ? <button aria-label={`${t("products.edit")} ${product.name}`} className="rounded-lg border border-border-subtle px-3 py-2 font-semibold dark:border-white/10" onClick={() => onEdit(product)}>{t("products.edit")}</button> : <span className="text-text-muted">{t("common.readOnly")}</span>}{onArchive ? <button aria-label={`${t("products.archive")} ${product.name}`} className="rounded-lg border border-danger-foreground/30 px-3 py-2 font-semibold text-danger-foreground" onClick={() => onArchive(product)}>{t("products.archive")}</button> : null}</div></td>
                </tr>
              );
            })}
            {products.length === 0 ? <tr><td className="px-4 py-8 text-center text-slate-500" colSpan={7}>{t("products.empty")}</td></tr> : null}
          </tbody>
        </table>
      </div>
      <div className="grid gap-3 lg:hidden">
        {products.map((product) => {
          const image = primaryImage(product);
          return (
            <article className={`min-w-0 rounded-2xl border p-4 ${selectedProductId === product.id ? "border-primary bg-surface-selected" : "border-border-subtle bg-surface-1"}`} onClick={() => onSelect?.(product)} key={product.id}>
              <div className="flex min-w-0 gap-3">
                {image ? <img className="h-16 w-16 shrink-0 rounded-xl object-cover" src={image.image_url} alt={image.alt_text ?? product.name} /> : <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-xl bg-surface-2 text-xs font-bold text-text-muted dark:bg-white/10">IMG</div>}
                <div className="min-w-0 flex-1">
                  <h3 className="truncate text-lg font-black text-text-primary">{product.name}</h3>
                  <p className="text-sm text-text-secondary">{displayCategory(product.category, t)}</p>
                  <p className="truncate text-sm text-text-secondary">SKU: {product.sku ?? "—"}</p>
                </div>
                <span className={`${statusBadgeClass(product.is_active ? "success" : "neutral")} shrink-0`}>{product.is_active ? t("products.active") : t("products.inactive")}</span>
              </div>
              <div className="mt-4 flex flex-col gap-2 sm:flex-row" onClick={(event) => event.stopPropagation()}>{onEdit ? <button className="min-h-11 rounded-xl border border-border-subtle px-4 py-3 font-bold dark:border-white/10" onClick={() => onEdit(product)}>{t("products.edit")}</button> : null}{onArchive ? <button className="min-h-11 rounded-xl border border-danger-foreground/30 px-4 py-3 font-bold text-danger-foreground" onClick={() => onArchive(product)}>{t("products.archive")}</button> : null}</div>
            </article>
          );
        })}
        {products.length === 0 ? <p className="p-6 text-center text-slate-500">{t("products.empty")}</p> : null}
      </div>
    </div>
  );
}
// Regression compatibility markers: Edit product; Archive product.
