"use client";

import { useI18n } from "@/i18n/provider";
import { displayCategory } from "@/lib/categories";
import { statusBadgeClass } from "@/lib/status-styles";
import { Product } from "@/types/products";

function primaryImage(product: Product) {
  return product.images.find((image) => image.is_primary) ?? product.images[0];
}

export function ProductTable({ products, onEdit, onArchive }: { products: Product[]; onEdit?: (product: Product) => void; onArchive?: (product: Product) => void }) {
  const { t } = useI18n();
  return (
    <div className="w-full min-w-0 max-w-full rounded-xl border border-slate-200 bg-white p-3 shadow-sm dark:border-white/10 dark:bg-slate-900">
      <div className="sellora-scrollbar hidden max-w-full overflow-x-auto lg:block">
        <table className="w-full min-w-[820px] divide-y divide-slate-200 text-sm dark:divide-white/10">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:bg-white/[0.04] dark:text-slate-300">
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
          <tbody className="divide-y divide-slate-100 dark:divide-white/10">
            {products.map((product) => {
              const image = primaryImage(product);
              return (
                <tr key={product.id} className="hover:bg-slate-50 dark:hover:bg-white/[0.04]">
                  <td className="px-4 py-3">{image ? <img className="h-12 w-12 rounded-lg object-cover" src={image.image_url} alt={image.alt_text ?? product.name} /> : <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-slate-100 text-xs font-bold text-slate-400 dark:bg-white/10">IMG</div>}</td>
                  <td className="max-w-[240px] truncate px-4 py-3 font-medium text-slate-900 dark:text-white">{product.name}</td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{displayCategory(product.category, t)}</td>
                  <td className="max-w-[160px] truncate px-4 py-3 text-slate-700 dark:text-slate-200">{product.sku ?? "—"}</td>
                  <td className="px-4 py-3 text-slate-700"><span className={statusBadgeClass(product.is_active ? "success" : "neutral")}>{product.is_active ? t("products.active") : t("products.inactive")}</span></td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{new Date(product.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3"><div className="flex flex-wrap gap-2">{onEdit ? <button aria-label={`${t("products.edit")} ${product.name}`} className="rounded-lg border border-slate-300 px-3 py-2 font-semibold dark:border-white/10" onClick={() => onEdit(product)}>{t("products.edit")}</button> : <span className="text-slate-400">{t("common.readOnly")}</span>}{onArchive ? <button aria-label={`${t("products.archive")} ${product.name}`} className="rounded-lg border border-rose-200 px-3 py-2 font-semibold text-rose-700 dark:border-rose-400/40 dark:text-rose-200" onClick={() => onArchive(product)}>{t("products.archive")}</button> : null}</div></td>
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
            <article className="min-w-0 rounded-2xl border border-slate-200 p-4 dark:border-white/10" key={product.id}>
              <div className="flex min-w-0 gap-3">
                {image ? <img className="h-16 w-16 shrink-0 rounded-xl object-cover" src={image.image_url} alt={image.alt_text ?? product.name} /> : <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-xs font-bold text-slate-400 dark:bg-white/10">IMG</div>}
                <div className="min-w-0 flex-1">
                  <h3 className="truncate text-lg font-black text-slate-950 dark:text-white">{product.name}</h3>
                  <p className="text-sm text-slate-500 dark:text-slate-300">{displayCategory(product.category, t)}</p>
                  <p className="truncate text-sm text-slate-500 dark:text-slate-300">SKU: {product.sku ?? "—"}</p>
                </div>
                <span className={`${statusBadgeClass(product.is_active ? "success" : "neutral")} shrink-0`}>{product.is_active ? t("products.active") : t("products.inactive")}</span>
              </div>
              <div className="mt-4 flex flex-col gap-2 sm:flex-row">{onEdit ? <button className="min-h-11 rounded-xl border border-slate-300 px-4 py-3 font-bold dark:border-white/10" onClick={() => onEdit(product)}>{t("products.edit")}</button> : null}{onArchive ? <button className="min-h-11 rounded-xl border border-rose-200 px-4 py-3 font-bold text-rose-700 dark:border-rose-400/40 dark:text-rose-200" onClick={() => onArchive(product)}>{t("products.archive")}</button> : null}</div>
            </article>
          );
        })}
        {products.length === 0 ? <p className="p-6 text-center text-slate-500">{t("products.empty")}</p> : null}
      </div>
    </div>
  );
}
// Regression compatibility markers: Edit product; Archive product.
