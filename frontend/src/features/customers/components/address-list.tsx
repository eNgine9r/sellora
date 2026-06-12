import { CustomerAddress } from "@/types/crm-completion";

export function AddressList({ addresses }: { addresses: CustomerAddress[] }) {
  return <div className="grid gap-2">{addresses.map((address) => <div key={address.id} className="rounded-lg border border-slate-200 p-3 text-sm"><div className="flex justify-between"><strong>{address.label ?? "Address"}</strong>{address.is_default ? <span className="text-blue-600">Default</span> : null}</div><p>{address.address_line1}</p><p className="text-slate-500">{[address.city, address.region, address.country].filter(Boolean).join(", ")}</p></div>)}{addresses.length === 0 ? <p className="text-sm text-slate-500">No addresses yet.</p> : null}</div>;
}
