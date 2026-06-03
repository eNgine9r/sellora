import { TopProduct } from "@/types/analytics";

export function TopProductsCard({ products }: { products: TopProduct[] }) {
  return <section className="rounded-[20px] border border-slate-100 bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.06)]"><h2 className="text-lg font-black">Top products</h2><div className="mt-4 grid gap-3">{products.slice(0, 5).map((product, index) => <div key={`${product.product_id}-${product.variant_id}`} className="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 p-3"><div><p className="font-bold text-slate-900">#{index + 1} {product.product_name}</p><p className="text-sm text-slate-500">{product.variant_sku} · {product.quantity_sold} sold</p></div><strong className="text-violet-700">${product.revenue}</strong></div>)}{products.length === 0 ? <p className="text-sm text-slate-500">No product data yet.</p> : null}</div></section>;
}
