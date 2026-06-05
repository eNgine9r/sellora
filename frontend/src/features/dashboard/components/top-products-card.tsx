import { EmptyState } from "@/components/ui/states";
import { formatMoney } from "@/lib/currency";
import { TopProduct } from "@/types/analytics";

export function TopProductsCard({ products, currencyCode = "UAH" }: { products: TopProduct[]; currencyCode?: string }) {
  const topProducts = products.slice(0, 5);

  return (
    <section className="min-w-0 overflow-hidden rounded-[20px] border border-slate-100 bg-white p-4 shadow-[0_18px_45px_rgba(15,23,42,0.06)] dark:border-white/10 dark:bg-slate-900 dark:shadow-none sm:p-5">
      <h2 className="break-words text-lg font-black text-slate-950 dark:text-white">Top products</h2>
      <p className="break-words text-sm text-slate-500 dark:text-slate-400">Best performers by revenue.</p>
      <div className="mt-4 grid min-w-0 gap-3">
        {topProducts.map((product, index) => (
          <div key={`${product.product_id}-${product.variant_id}`} className="flex min-w-0 items-center justify-between gap-3 overflow-hidden rounded-2xl bg-slate-50 p-3 transition hover:bg-violet-50/70 dark:bg-white/[0.05] dark:hover:bg-violet-400/10">
            <div className="min-w-0 overflow-hidden">
              <p className="truncate font-bold text-slate-900 dark:text-white">#{index + 1} {product.product_name}</p>
              <p className="truncate text-sm text-slate-500 dark:text-slate-400">{product.variant_sku} · {product.quantity_sold} sold</p>
            </div>
            <strong className="shrink-0 whitespace-nowrap text-sm text-violet-700 dark:text-violet-200">{formatMoney(product.revenue, currencyCode)}</strong>
          </div>
        ))}
        {topProducts.length === 0 ? <EmptyState title="No product data yet" description="Product performance will appear after orders are created or imported." /> : null}
      </div>
    </section>
  );
}
