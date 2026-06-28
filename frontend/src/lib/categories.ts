import { Product } from "@/types/products";

export const CATEGORY_KEYS = ["rings", "earrings", "pendants", "bracelets", "chains", "sets", "watches", "other"] as const;
export type CategoryKey = (typeof CATEGORY_KEYS)[number];
export type CategoryFilter = "all" | CategoryKey;

type Translate = (key: string) => string;

const CATEGORY_ALIASES: Record<string, CategoryKey> = {
  ring: "rings",
  rings: "rings",
  каблучка: "rings",
  каблучки: "rings",
  перстень: "rings",
  персні: "rings",
  earring: "earrings",
  earrings: "earrings",
  сережка: "earrings",
  сережки: "earrings",
  pendant: "pendants",
  pendants: "pendants",
  підвіска: "pendants",
  підвіски: "pendants",
  кулон: "pendants",
  кулони: "pendants",
  bracelet: "bracelets",
  bracelets: "bracelets",
  браслет: "bracelets",
  браслети: "bracelets",
  chain: "chains",
  chains: "chains",
  ланцюжок: "chains",
  ланцюжки: "chains",
  set: "sets",
  sets: "sets",
  комплект: "sets",
  комплекти: "sets",
  watch: "watches",
  watches: "watches",
  годинник: "watches",
  годинники: "watches",
  other: "other",
  інше: "other",
};

export function normalizeCategoryKey(category?: string | null): CategoryKey {
  const normalized = category?.trim().toLowerCase();
  if (!normalized) return "other";
  return CATEGORY_ALIASES[normalized] ?? (CATEGORY_KEYS.includes(normalized as CategoryKey) ? (normalized as CategoryKey) : "other");
}

export function categoryMatches(category: string | null | undefined, filter: CategoryFilter) {
  return filter === "all" || normalizeCategoryKey(category) === filter;
}

export function translatedCategoryOptions(t: Translate) {
  return CATEGORY_KEYS.map((key) => ({ value: key, label: t(`categories.${key}`) }));
}

export function displayCategory(category: string | null | undefined, t: Translate) {
  const raw = category?.trim();
  if (!raw) return t("categories.other");
  const key = normalizeCategoryKey(raw);
  if (CATEGORY_ALIASES[raw.toLowerCase()] || CATEGORY_KEYS.includes(raw.toLowerCase() as CategoryKey)) return t(`categories.${key}`);
  return raw;
}

export function productSearchMatches(product: Product, search: string) {
  const query = search.trim().toLowerCase();
  if (!query) return true;
  return [product.name, product.sku, product.category, product.brand].filter(Boolean).some((value) => String(value).toLowerCase().includes(query));
}
