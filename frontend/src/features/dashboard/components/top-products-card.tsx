import { RemoteImage } from "@/components/ui/remote-image";
import { EmptyState } from "@/components/ui/states";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import { TopProduct } from "@/types/analytics";

export type TopProductView = TopProduct & { categoryLabel?: string; imageUrl?: string | null };

export function TopProductsCard({ products, currencyCode = "UAH", showProfit = false }: { products: TopProductView[]; currencyCode?: string; showProfit?: boolean }) {
  const { t } = useI18n();
  const topProducts = products.slice(0, 5);

  return (
    <section className="min-w-0 overflow-hidden rounded-xl border border-border-subtle bg-surface-1 p-3 sm:p-4">
      <h2 className="break-words text-sm font-semibold text-text-primary sm:text-base">{t("dashboard.topProducts.title")}</h2>
      <p className="break-words text-xs text-text-secondary">{t("dashboard.topProducts.subtitle")}</p>
      <div className="mt-3 grid min-w-0 gap-1.5">
        {topProducts.map((product, index) => (
          <div key={`${product.product_id}-${product.variant_id}`} className="flex min-w-0 items-center justify-between gap-3 overflow-hidden rounded-lg bg-surface-2 px-2.5 py-2 transition hover:bg-surface-hover">
            {product.imageUrl ? <RemoteImage className="h-9 w-9 shrink-0 rounded-lg" src={product.imageUrl} alt={product.product_name} /> : <span className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-surface-3 text-xs font-semibold text-text-secondary">{index + 1}</span>}
            <div className="min-w-0 flex-1 overflow-hidden">
              <p className="truncate text-xs font-semibold text-text-primary sm:text-sm">#{index + 1} {product.product_name}</p>
              <p className="truncate text-xs text-text-secondary">{product.variant_sku} · {product.categoryLabel ?? t("categories.other")} · {product.quantity_sold} {t("dashboard.topProducts.sold")}</p>
            </div>
            <div className="shrink-0 text-right"><strong className="block whitespace-nowrap text-xs text-primary">{formatMoney(product.revenue, currencyCode)}</strong>{showProfit ? <span className="text-[11px] text-text-muted">{formatMoney(product.net_profit, currencyCode)}</span> : null}</div>
          </div>
        ))}
        {topProducts.length === 0 ? <EmptyState title={t("dashboard.emptyStates.noTopProducts")} description={t("dashboard.emptyStates.noTopProductsDescription")} /> : null}
      </div>
    </section>
  );
}
