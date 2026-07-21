"use client";

import { FormEvent, useState } from "react";
import { buildProductVariantCreatePayload } from "@/lib/payload-builders";
import { ProductVariantCreatePayload } from "@/services/products";
import { Product } from "@/types/products";
import { useI18n } from "@/i18n/provider";
import { Button, FormField, Input, Select } from "@/components/ui/primitives";

export type ProductVariantFormValues = {
  product_id: string;
  sku: string;
  color?: string;
  size?: string;
  price?: string;
  initial_stock_quantity?: string;
  minimum_quantity?: string;
};

export function ProductVariantForm({ products, onSubmit, isSubmitting = false, submitError }: { products: Product[]; onSubmit: (values: ProductVariantCreatePayload) => void; isSubmitting?: boolean; submitError?: string | null }) {
  const { t } = useI18n();
  const [values, setValues] = useState<ProductVariantFormValues>({ product_id: "", sku: "", initial_stock_quantity: "0", minimum_quantity: "0" });
  const [validationError, setValidationError] = useState<string | null>(null);
  const hasProducts = products.length > 0;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!hasProducts) {
      setValidationError(t("products.createProductVariantFirst"));
      return;
    }
    const payload = buildProductVariantCreatePayload(values);
    if (!payload.product_id || !payload.sku) {
      setValidationError(t("errors.required"));
      return;
    }
    setValidationError(null);
    onSubmit(payload);
  }

  return (
    <form className="grid w-full min-w-0 gap-4 overflow-x-hidden" onSubmit={submit} noValidate>
      {!hasProducts ? <p className="rounded-2xl border border-warning/25 bg-[var(--warning-surface)] px-3 py-2 text-sm font-bold text-[var(--warning-foreground)]">{t("products.createProductVariantFirst")}</p> : null}
      <FormField label={t("inventory.product")}>
        <Select value={values.product_id} onChange={(event) => setValues({ ...values, product_id: event.target.value })} disabled={!hasProducts}>
          <option value="">Оберіть товар</option>
          {products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}
        </Select>
      </FormField>
      <FormField label={t("products.variantSku")} error={validationError}>
        <Input value={values.sku} onChange={(event) => setValues({ ...values, sku: event.target.value })} />
      </FormField>
      <div className="grid min-w-0 gap-4 sm:grid-cols-2">
        <FormField label={t("products.color")}><Input value={values.color ?? ""} onChange={(event) => setValues({ ...values, color: event.target.value })} /></FormField>
        <FormField label={t("products.size")}><Input value={values.size ?? ""} onChange={(event) => setValues({ ...values, size: event.target.value })} /></FormField>
      </div>
      <div className="grid min-w-0 gap-4 sm:grid-cols-2">
        <FormField label={t("products.sellingPrice")}><Input inputMode="decimal" type="number" min="0" step="0.01" value={values.price ?? ""} onChange={(event) => setValues({ ...values, price: event.target.value })} /></FormField>
        <FormField label="Початковий залишок"><Input min="0" type="number" value={values.initial_stock_quantity ?? "0"} onChange={(event) => setValues({ ...values, initial_stock_quantity: event.target.value })} /></FormField>
      </div>
      <FormField label={t("tables.minimum")}><Input min="0" type="number" value={values.minimum_quantity ?? "0"} onChange={(event) => setValues({ ...values, minimum_quantity: event.target.value })} /></FormField>
      {submitError ? <p className="rounded-2xl border border-danger/25 bg-[var(--danger-surface)] px-3 py-2 text-sm font-bold text-[var(--danger-foreground)]">{submitError}</p> : null}
      <Button className="w-full" loading={isSubmitting} disabled={!hasProducts} type="submit">{t("products.createVariant")}</Button>
    </form>
  );
}
