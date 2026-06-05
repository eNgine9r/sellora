import { existsSync, readFileSync } from "node:fs";

const read = (path) => readFileSync(path, "utf8");
const checks = [];
function assert(condition, label) {
  if (!condition) throw new Error(label);
  checks.push(label);
}

const pagination = read("frontend/src/components/pagination-controls.tsx");
const productsPage = read("frontend/src/app/products/page.tsx");
const inventoryPage = read("frontend/src/app/inventory/page.tsx");
const orderForm = read("frontend/src/features/orders/components/order-form.tsx");
const shipmentsPage = read("frontend/src/app/shipments/page.tsx");
const shipmentTable = read("frontend/src/features/shipments/components/shipment-table.tsx");
const shipmentDetails = read("frontend/src/features/shipments/components/shipment-details.tsx");
const en = read("frontend/src/i18n/messages/en.json");
const uk = read("frontend/src/i18n/messages/uk.json");

assert(existsSync("frontend/src/components/pagination-controls.tsx") && pagination.includes("PaginationControls"), "shared PaginationControls exists");
assert(pagination.includes("[5, 15, 30]") && pagination.includes("pagination.previous") && pagination.includes("pagination.next"), "page size options 5/15/30 and localized controls exist");
assert(productsPage.includes("paginatedProducts") && productsPage.includes("productPageSize") && productsPage.includes("PaginationControls"), "products page uses pagination");
assert(productsPage.includes("paginatedVariants") && productsPage.includes("variantPageSize") && productsPage.includes("PaginationControls"), "product variants list uses pagination");
assert(inventoryPage.includes("paginatedInventory") && inventoryPage.includes("inventoryPageSize") && inventoryPage.includes("PaginationControls"), "inventory page uses pagination");
assert(productsPage.includes("categoryFilter") && productsPage.includes("productSearchMatches") && inventoryPage.includes("categoryMatches"), "pagination works with category/search markers");
assert(orderForm.includes("productImage(product)") && orderForm.includes("orders.productOption.noImage") && orderForm.includes("slice(0, 8)"), "order product selector supports image/placeholder and limited option rendering");
assert(shipmentsPage.includes("shipments.logisticsLabel") && shipmentsPage.includes("common.searchByTrackingNumber") && shipmentDetails.includes("formatStatus(\"shipment\"") && uk.includes("Логістика Sellora"), "shipments page has localized shipment keys");
assert(shipmentTable.includes("sellora-scrollbar") && shipmentTable.includes("md:hidden"), "shipments table uses Sellora scrollbar and mobile cards");
assert(en.includes('"pagination"') && uk.includes('"pagination"') && en.includes('"productOption"') && uk.includes('"productOption"'), "new pagination and product option strings use i18n keys");
assert(productsPage.includes("min-w-0") && inventoryPage.includes("overflow-hidden") && shipmentTable.includes("dark:"), "existing localization/theme/responsive markers remain");

console.log(`Pagination/list UX regression passed (${checks.length} checks).`);
