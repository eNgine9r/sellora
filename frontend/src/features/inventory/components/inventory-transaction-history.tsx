import { InventoryTransaction, InventoryTransactionType } from "@/types/products";
import { useI18n } from "@/i18n/provider";

function reasonKey(reason?: string | null) {
  const normalized = (reason ?? "").trim().toLowerCase().replaceAll(" ", "_");
  return normalized ? `inventory.transactionReasons.${normalized}` : "";
}

export function transactionTypeLabel(t: (key: string) => string, type: InventoryTransactionType) {
  const label = t(`inventory.transactionTypes.${type}`);
  return label.startsWith("inventory.transactionTypes.") ? type : label;
}

export function transactionReasonLabel(t: (key: string) => string, reason?: string | null) {
  const key = reasonKey(reason);
  if (!key) return "";
  const label = t(key);
  return label === key ? reason ?? "" : label;
}

export function InventoryTransactionHistory({ transactions }: { transactions: InventoryTransaction[] }) {
  const { t } = useI18n();
  return (
    <section className="rounded-2xl bg-white p-4 shadow-sm dark:bg-[#15172A]">
      <h2 className="mb-3 text-lg font-semibold text-slate-950 dark:text-white">{t("inventory.transactionHistory")}</h2>
      <div className="sellora-scrollbar grid max-h-[28rem] gap-2 overflow-y-auto pr-1">
        {transactions.map((transaction) => (
          <article className="rounded-xl border border-slate-100 p-3 text-sm dark:border-white/10" key={transaction.id}>
            <strong className="text-slate-950 dark:text-white">{transactionTypeLabel(t, transaction.transaction_type)}</strong>
            <p className="text-slate-600 dark:text-slate-300">{t("inventory.qty")} {transaction.quantity}: {t("inventory.stockLabel")} {transaction.previous_stock_quantity} → {transaction.new_stock_quantity}, {t("inventory.reservedLabel")} {transaction.previous_reserved_quantity} → {transaction.new_reserved_quantity}</p>
            {transaction.reason ? <p className="text-xs text-slate-500 dark:text-slate-400">{transactionReasonLabel(t, transaction.reason)}</p> : null}
          </article>
        ))}
        {transactions.length === 0 ? <p className="text-sm text-slate-500 dark:text-slate-300">{t("inventory.noTransactionsYet")}</p> : null}
      </div>
    </section>
  );
}
