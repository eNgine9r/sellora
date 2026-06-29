import { readFileSync, existsSync } from "node:fs";

const checks = [];
const read = (path) => readFileSync(path, "utf8");
const assert = (condition, message) => {
  if (!condition) throw new Error(message);
  checks.push(message);
};

const productsPage = read("frontend/src/app/products/page.tsx");
const productTable = read("frontend/src/features/products/components/product-table.tsx");
const productForm = read("frontend/src/features/products/components/product-form.tsx");
const orderForm = read("frontend/src/features/orders/components/order-form.tsx");
const inventoryPage = read("frontend/src/app/inventory/page.tsx");
const inventoryTable = read("frontend/src/features/inventory/components/inventory-table.tsx");
const categories = read("frontend/src/lib/categories.ts");
const uk = read("frontend/src/i18n/messages/uk.json");
const en = read("frontend/src/i18n/messages/en.json");

assert(existsSync("frontend/src/lib/categories.ts"), "category utility exists");
assert(categories.includes("CATEGORY_KEYS") && categories.includes("normalizeCategoryKey") && categories.includes("categoryMatches"), "category normalization and filtering helpers exist");
assert(productsPage.includes("categoryFilter") && productsPage.includes("categories.allProducts") && productsPage.includes("productSearchMatches"), "products page has category filter chips/search markers");
assert(productTable.includes("products.category") && productTable.includes("displayCategory") && productTable.includes("lg:hidden"), "product table/cards show localized category");
assert(productForm.includes("products.productCategory") && productForm.includes("translatedCategoryOptions") && productForm.includes("category"), "product form supports localized category select");
assert(orderForm.includes("orders.selectCategory") && orderForm.includes("selectCategory") && orderForm.includes("CategoryFilter"), "order form has category selector per item");
assert(orderForm.includes("orders.searchProduct") && orderForm.includes("selectProduct") && orderForm.includes("filteredProducts"), "order form has product selector/search scoped by category");
assert(orderForm.includes("variantOptions") && orderForm.includes("orders.available") && orderForm.includes("formatMoney"), "variant selector is scoped and shows stock/price labels");
assert(inventoryTable.includes("inventory.productImage") && inventoryTable.includes("inventory.category") && inventoryTable.includes("inventory.product") && inventoryTable.includes("tables.variantSku"), "inventory table/card displays image category product and variant SKU");
assert(inventoryPage.includes("inventory.filterByCategory") && inventoryPage.includes("categoryMatches") && inventoryPage.includes("visibleInventory"), "inventory page has category filter and filtered rows");
assert(uk.includes('"categories"') && en.includes('"categories"') && uk.includes("Каблучки") && en.includes("Rings"), "category i18n keys exist in uk/en dictionaries");
assert(productsPage.includes("sellora-scrollbar") && inventoryTable.includes("sellora-scrollbar") && orderForm.includes("min-w-0"), "responsive/theme scrollbar markers preserved");

console.log(`Catalog inventory UX regression passed (${checks.length} checks).`);
