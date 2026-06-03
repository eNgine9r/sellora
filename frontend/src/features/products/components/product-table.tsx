import { Product } from "@/types/products";

export function ProductTable({ products }: { products: Product[] }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-3">Image</th>
            <th className="px-4 py-3">Name</th>
            <th className="px-4 py-3">SKU</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Created</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {products.map((product) => {
            const primaryImage = product.images.find((image) => image.is_primary) ?? product.images[0];
            return (
              <tr key={product.id} className="hover:bg-slate-50">
                <td className="px-4 py-3">{primaryImage ? <img className="h-12 w-12 rounded-lg object-cover" src={primaryImage.image_url} alt={primaryImage.alt_text ?? product.name} /> : "—"}</td>
                <td className="px-4 py-3 font-medium text-slate-900">{product.name}</td>
                <td className="px-4 py-3 text-slate-700">{product.sku ?? "—"}</td>
                <td className="px-4 py-3 text-slate-700">{product.is_active ? "Active" : "Inactive"}</td>
                <td className="px-4 py-3 text-slate-700">{new Date(product.created_at).toLocaleDateString()}</td>
              </tr>
            );
          })}
          {products.length === 0 ? <tr><td className="px-4 py-8 text-center text-slate-500" colSpan={5}>No products found.</td></tr> : null}
        </tbody>
      </table>
    </div>
  );
}
