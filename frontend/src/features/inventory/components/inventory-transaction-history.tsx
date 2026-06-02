import { InventoryTransaction } from "@/types/products";

export function InventoryTransactionHistory({ transactions }: { transactions: InventoryTransaction[] }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-lg font-semibold">Transaction history</h2>
      <div className="grid gap-3">
        {transactions.map((transaction) => (
          <div key={transaction.id} className="rounded-lg border border-slate-100 p-3 text-sm">
            <div className="flex justify-between"><strong>{transaction.transaction_type}</strong><span>{new Date(transaction.created_at).toLocaleString()}</span></div>
            <p className="text-slate-600">Qty {transaction.quantity}: stock {transaction.previous_stock_quantity} → {transaction.new_stock_quantity}, reserved {transaction.previous_reserved_quantity} → {transaction.new_reserved_quantity}</p>
            {transaction.reason ? <p className="text-slate-500">{transaction.reason}</p> : null}
          </div>
        ))}
        {transactions.length === 0 ? <p className="text-sm text-slate-500">No transactions yet.</p> : null}
      </div>
    </div>
  );
}
