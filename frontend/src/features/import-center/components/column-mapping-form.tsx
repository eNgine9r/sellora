"use client";

import { getImportCenterPilotCopy, importFieldLabel } from "@/features/import-center/import-center-pilot-copy";
import { useI18n } from "@/i18n/provider";

const fields: Record<string, string[]> = {
  customers: ["name", "phone", "instagram_username", "city", "region"],
  products: ["name", "sku", "description"],
  product_variants: ["product_name", "product_sku", "variant_sku", "color", "size", "selling_price"],
  inventory: ["variant_sku", "stock_quantity", "reserved_quantity", "minimum_quantity"],
  orders: ["customer_name", "customer_phone", "instagram_username", "revenue", "order_total", "created_at", "order_date", "ad_cost", "shipping_cost", "cod_fee", "other_cost", "net_profit"],
};

export function ColumnMappingForm({ entityType, columns, mapping, onChange }: { entityType: string; columns: string[]; mapping: Record<string, string>; onChange: (mapping: Record<string, string>) => void }) {
  const { locale } = useI18n();
  const labels = getImportCenterPilotCopy(locale);
  return (
    <div className="w-full min-w-0 max-w-full overflow-hidden rounded-xl bg-white p-4 shadow-sm" data-import-column-mapping>
      <h2 className="mb-3 font-semibold">{labels.columnMapping}</h2>
      <div className="grid min-w-0 gap-3 md:grid-cols-2">
        {(fields[entityType] ?? []).map((field) => (
          <label className="grid min-w-0 gap-1 text-sm" key={field}>
            <span className="min-w-0 truncate" title={importFieldLabel(field, locale)}>{importFieldLabel(field, locale)}</span>
            <select className="w-full min-w-0 max-w-full truncate rounded-md border border-slate-300 px-2 py-1" value={mapping[field] ?? ""} onChange={(event) => onChange({ ...mapping, [field]: event.target.value })}>
              <option value="">{labels.notMapped}</option>
              {columns.map((column) => <option key={column} value={column}>{column}</option>)}
            </select>
          </label>
        ))}
      </div>
    </div>
  );
}
