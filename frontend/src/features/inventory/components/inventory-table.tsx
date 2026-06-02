import { Inventory, ProductVariant } from "@/types/products";

export function InventoryTable({ inventory, variants }: { inventory: Inventory[]; variants: ProductVariant[] }) {
  const variantById = new Map(variants.map((variant) => [variant.id, variant]));
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
          <tr><th className="px-4 py-3">Variant SKU</th><th className="px-4 py-3">Stock</th><th className="px-4 py-3">Reserved</th><th className="px-4 py-3">Minimum</th><th className="px-4 py-3">Status</th></tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {inventory.map((item) => {
            const variant = variantById.get(item.product_variant_id);
            return <tr key={item.id} className="hover:bg-slate-50"><td className="px-4 py-3 font-medium text-slate-900">{variant?.sku ?? item.product_variant_id}</td><td className="px-4 py-3">{item.stock_quantity}</td><td className="px-4 py-3">{item.reserved_quantity}</td><td className="px-4 py-3">{item.minimum_quantity}</td><td className="px-4 py-3">{item.is_low_stock ? <span className="rounded-full bg-rose-100 px-3 py-1 text-xs font-semibold text-rose-700">Low stock</span> : <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">Healthy</span>}</td></tr>;
          })}
          {inventory.length === 0 ? <tr><td className="px-4 py-8 text-center text-slate-500" colSpan={5}>No inventory records found.</td></tr> : null}
        </tbody>
      </table>
    </div>
  );
}
