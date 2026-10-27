/** Prefill only an untouched single draft row after the manager selects a variant. */
export function prefillSuggestedVariant<T extends { product_variant_id: string; unit_price: string; unit_cost: string }>(
  items: T[], variant: { id: string; price: string | null },
): T[] {
  if (items.length !== 1 || items[0].product_variant_id) return items;
  return [{ ...items[0], product_variant_id: variant.id, unit_price: variant.price ?? "", unit_cost: "" }];
}
