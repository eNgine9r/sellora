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

export function InventoryTransactionHistory({ transactions, compact = false }: { transactions: InventoryTransaction[]; compact?: boolean }) {
  const { t } = useI18n();
  return (
    <section className="rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm">
      {compact ? null : <h2 className="mb-3 text-lg font-semibold text-text-primary">{t("inventory.transactionHistory")}</h2>}
      <div className="sellora-scrollbar grid max-h-[28rem] gap-2 overflow-y-auto pr-1">
        {transactions.map((transaction) => (
          <article className="rounded-xl border border-border-subtle bg-surface-2 p-3 text-sm" key={transaction.id}>
            <strong className="text-text-primary">{transactionTypeLabel(t, transaction.transaction_type)}</strong>
            <p className="text-text-secondary">{t("inventory.qty")} {transaction.quantity}: {t("inventory.stockLabel")} {transaction.previous_stock_quantity} → {transaction.new_stock_quantity}, {t("inventory.reservedLabel")} {transaction.previous_reserved_quantity} → {transaction.new_reserved_quantity}</p>
            {transaction.reason ? <p className="text-xs text-text-muted">{transactionReasonLabel(t, transaction.reason)}</p> : null}
          </article>
        ))}
        {transactions.length === 0 ? <p className="text-sm text-text-muted">{t("inventory.noTransactionsYet")}</p> : null}
      </div>
    </section>
  );
}
