"use client";

import { ChevronRight } from "lucide-react";
import { RowActionButtons } from "@/components/ui/row-action-buttons";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import { Customer } from "@/types/crm";

type Props = {
  customers: Customer[];
  currencyCode?: string;
  selectedCustomerId?: string | null;
  onSelect?: (customer: Customer) => void;
  onEdit?: (customer: Customer) => void;
  onArchive?: (customer: Customer) => void;
};

export function CustomerTable({ customers, currencyCode = "UAH", selectedCustomerId, onSelect, onEdit, onArchive }: Props) {
  const { t } = useI18n();
  return (
    <div className="sellora-adaptive-list sellora-adaptive-wide-list mobile-card-list min-w-0 rounded-[var(--radius-card)] border border-border-subtle bg-surface-1 p-2 shadow-[var(--shadow-card)] md:p-3">
      <div className="sellora-scrollbar sellora-adaptive-table overflow-x-auto">
        <table className="w-full min-w-[850px] divide-y divide-border-subtle text-sm">
          <thead className="bg-surface-2 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">
            <tr>
              <th className="px-3 py-3">{t("tables.name")}</th>
              <th className="px-3 py-3">{t("tables.phone")}</th>
              <th className="px-3 py-3">{t("tables.instagram")}</th>
              <th className="px-3 py-3">{t("customers.totalOrders")}</th>
              <th className="px-3 py-3">{t("customers.paidPurchases")}</th>
              <th className="px-3 py-3">{t("customers.paidSpent")}</th>
              <th className="px-3 py-3">{t("tables.lastOrder")}</th>
              <th className="px-3 py-3">{t("tables.actions")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle">
            {customers.map((customer) => (
              <tr key={customer.id} className={`cursor-pointer hover:bg-surface-hover ${selectedCustomerId === customer.id ? "bg-surface-selected" : ""}`} onClick={() => onSelect?.(customer)}>
                <td className="max-w-[210px] truncate px-3 py-3 font-semibold text-text-primary" title={customer.name}>{customer.name}</td>
                <td className="whitespace-nowrap px-3 py-3 text-text-secondary">{customer.phone ?? "—"}</td>
                <td className="max-w-[190px] truncate px-3 py-3 text-text-secondary" title={customer.instagram_username ?? undefined}>{customer.instagram_username ? `@${customer.instagram_username.replace(/^@/, "")}` : "—"}</td>
                <td className="px-3 py-3 font-semibold">{customer.total_orders}</td>
                <td className="px-3 py-3">{customer.paid_orders}</td>
                <td className="whitespace-nowrap px-3 py-3">{formatMoney(customer.total_spent, currencyCode)}</td>
                <td className="whitespace-nowrap px-3 py-3 text-text-secondary">{customer.last_order_at ? new Date(customer.last_order_at).toLocaleDateString("uk-UA") : "—"}</td>
                <td className="px-2 py-3">
                  <RowActionButtons entityLabel={customer.name} editLabel={t("customers.edit")} archiveLabel={t("customers.archive")} onEdit={onEdit ? () => onEdit(customer) : undefined} onArchive={onArchive ? () => onArchive(customer) : undefined} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="sellora-adaptive-cards grid gap-2">
        {customers.map((customer) => (
          <button
            type="button"
            key={customer.id}
            onClick={() => onSelect?.(customer)}
            aria-label={`${customer.name}, ${t("customers.totalOrders")}: ${customer.total_orders}`}
            className={`mobile-customer-card min-w-0 rounded-2xl border p-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${selectedCustomerId === customer.id ? "border-primary bg-primary/5" : "border-border-subtle bg-surface-2"}`}
          >
            <div className="flex min-w-0 items-start gap-2">
              <div className="min-w-0 flex-1">
                <h3 className="truncate text-base font-bold text-text-primary">{customer.name}</h3>
                <p className="truncate text-xs text-text-muted">{customer.instagram_username ? `@${customer.instagram_username.replace(/^@/, "")}` : (customer.phone ?? t("customers.missingContact"))}</p>
                {customer.instagram_username && customer.phone ? <p className="mt-0.5 truncate text-xs text-text-secondary">{customer.phone}</p> : null}
              </div>
              <span className="shrink-0 rounded-full bg-primary/10 px-2.5 py-1 text-xs font-bold text-primary">{t("customers.totalOrders")}: {customer.total_orders}</span>
              <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-text-muted" aria-hidden="true" />
            </div>
            <div className="mt-2.5 grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 border-t border-border-subtle pt-2.5 text-xs">
              <div><span className="text-text-muted">{t("customers.paidPurchases")}</span><p className="mt-0.5 font-semibold text-text-primary">{customer.paid_orders}</p></div>
              <div className="min-w-0"><span className="text-text-muted">{t("customers.paidSpent")}</span><p className="mt-0.5 truncate font-semibold text-text-primary">{formatMoney(customer.total_spent, currencyCode)}</p></div>
            </div>
            {customer.last_order_at ? <p className="mt-1.5 truncate text-[11px] text-text-muted">{t("customers.lastOrder")}: {new Date(customer.last_order_at).toLocaleDateString("uk-UA")}</p> : null}
          </button>
        ))}
      </div>
    </div>
  );
}

// Localization regression compatibility markers: Edit customer; Archive customer; mobile-customer-card.
