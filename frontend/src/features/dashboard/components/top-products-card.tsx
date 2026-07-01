import { EmptyState } from "@/components/ui/states";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import { TopProduct } from "@/types/analytics";

export type TopProductView = TopProduct & { categoryLabel?: string; imageUrl?: string | null };

export function TopProductsCard({ products, currencyCode = "UAH", showProfit = false }: { products: TopProductView[]; currencyCode?: string; showProfit?: boolean }) {
  const { t } = useI18n();
  const topProducts = products.slice(0, 5);

  return (
    <section className="min-w-0 overflow-hidden rounded-[20px] border border-slate-100 bg-white p-4 shadow-[0_18px_45px_rgba(15,23,42,0.06)] dark:border-white/10 dark:bg-slate-900 dark:shadow-none sm:p-5">
      <h2 className="break-words text-lg font-black text-slate-950 dark:text-white">{t("dashboard.topProducts.title")}</h2>
      <p className="break-words text-sm text-slate-500 dark:text-slate-400">{t("dashboard.topProducts.subtitle")}</p>
      <div className="mt-4 grid min-w-0 gap-3">
        {topProducts.map((product, index) => (
          <div key={`${product.product_id}-${product.variant_id}`} className="flex min-w-0 items-center justify-between gap-3 overflow-hidden rounded-2xl bg-slate-50 p-3 transition hover:bg-violet-50/70 dark:bg-white/[0.05] dark:hover:bg-violet-400/10">
            {product.imageUrl ? <img className="h-11 w-11 shrink-0 rounded-xl object-cover" src={product.imageUrl} alt={product.product_name} /> : <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-white text-xs font-black text-slate-400 dark:bg-white/10">{index + 1}</span>}
            <div className="min-w-0 flex-1 overflow-hidden">
              <p className="truncate font-bold text-slate-900 dark:text-white">#{index + 1} {product.product_name}</p>
              <p className="truncate text-sm text-slate-500 dark:text-slate-400">{product.variant_sku} · {product.categoryLabel ?? t("categories.other")} · {product.quantity_sold} {t("dashboard.topProducts.sold")}</p>
            </div>
            <div className="shrink-0 text-right"><strong className="block whitespace-nowrap text-sm text-violet-700 dark:text-violet-200">{formatMoney(product.revenue, currencyCode)}</strong>{showProfit ? <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-200">{formatMoney(product.net_profit, currencyCode)}</span> : null}</div>
          </div>
        ))}
        {topProducts.length === 0 ? <EmptyState title={t("dashboard.emptyStates.noTopProducts")} description={t("dashboard.emptyStates.noTopProductsDescription")} /> : null}
      </div>
    </section>
  );
}
