import { EmptyState } from "@/components/ui/states";
import { formatMoney } from "@/lib/currency";
import { TopProduct } from "@/types/analytics";

export function TopProductsCard({ products, currencyCode = "UAH" }: { products: TopProduct[]; currencyCode?: string }) {
  const topProducts = products.slice(0, 5);

  return (
    <section className="rounded-[20px] border border-slate-100 bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.06)]">
      <h2 className="text-lg font-black">Top products</h2>
      <p className="text-sm text-slate-500">Best performers by revenue.</p>
      <div className="mt-4 grid gap-3">
        {topProducts.map((product, index) => (
          <div key={`${product.product_id}-${product.variant_id}`} className="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 p-3 transition hover:bg-violet-50/70">
            <div className="min-w-0">
              <p className="truncate font-bold text-slate-900">
                #{index + 1} {product.product_name}
              </p>
              <p className="truncate text-sm text-slate-500">
                {product.variant_sku} · {product.quantity_sold} sold
              </p>
            </div>
            <strong className="shrink-0 text-violet-700">{formatMoney(product.revenue, currencyCode)}</strong>
          </div>
        ))}
        {topProducts.length === 0 ? <EmptyState title="No product data yet" description="Product performance will appear after orders are created or imported." /> : null}
      </div>
    </section>
  );
}
