import { Customer } from "@/types/crm";

export function CustomerTable({ customers }: { customers: Customer[] }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-3">Name</th>
            <th className="px-4 py-3">Phone</th>
            <th className="px-4 py-3">Instagram</th>
            <th className="px-4 py-3">Orders</th>
            <th className="px-4 py-3">Spent</th>
            <th className="px-4 py-3">Last Order</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {customers.map((customer) => (
            <tr key={customer.id} className="hover:bg-slate-50">
              <td className="px-4 py-3 font-medium text-slate-900">{customer.name}</td>
              <td className="px-4 py-3 text-slate-700">{customer.phone ?? "—"}</td>
              <td className="px-4 py-3 text-slate-700">{customer.instagram_username ?? "—"}</td>
              <td className="px-4 py-3 text-slate-700">{customer.total_orders}</td>
              <td className="px-4 py-3 text-slate-700">${customer.total_spent}</td>
              <td className="px-4 py-3 text-slate-700">{customer.last_order_at ? new Date(customer.last_order_at).toLocaleDateString() : "—"}</td>
            </tr>
          ))}
          {customers.length === 0 ? (
            <tr><td className="px-4 py-8 text-center text-slate-500" colSpan={6}>No customers found.</td></tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
