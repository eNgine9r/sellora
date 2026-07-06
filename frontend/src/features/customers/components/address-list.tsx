import { CustomerAddress } from "@/types/crm-completion";
import { useI18n } from "@/i18n/provider";

export function AddressList({ addresses }: { addresses: CustomerAddress[] }) {
  const { t } = useI18n();
  return <div className="grid gap-2">{addresses.map((address) => <div key={address.id} className="rounded-lg border border-slate-200 p-3 text-sm"><div className="flex justify-between"><strong>{address.label ?? t("customers.address")}</strong>{address.is_default ? <span className="text-blue-600">{t("customers.defaultAddress")}</span> : null}</div><p>{address.address_line1}</p><p className="text-slate-500">{[address.city, address.region, address.country].filter(Boolean).join(", ")}</p></div>)}{addresses.length === 0 ? <p className="text-sm text-slate-500">{t("customers.noAddresses")}</p> : null}</div>;
}
