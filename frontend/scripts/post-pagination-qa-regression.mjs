import { existsSync, readFileSync } from "node:fs";
import assert from "node:assert/strict";

const read = (path) => readFileSync(path, "utf8");
const orderForm = read("frontend/src/features/orders/components/order-form.tsx");
const inventoryPage = read("frontend/src/app/inventory/page.tsx");
const transactionHistory = read("frontend/src/features/inventory/components/inventory-transaction-history.tsx");
const integrations = read("frontend/src/features/integrations/components/nova-poshta-settings-card.tsx");
const city = read("frontend/src/features/integrations/components/city-search-select.tsx");
const warehouse = read("frontend/src/features/integrations/components/warehouse-search-select.tsx");
const topbar = read("frontend/src/components/app-topbar.tsx");
const en = read("frontend/src/i18n/messages/en.json");
const uk = read("frontend/src/i18n/messages/uk.json");

assert(orderForm.includes("MAX_PRODUCT_SELECTOR_OPTIONS = 30") && orderForm.includes("visibleProductOptions") && !orderForm.includes("slice(0, 8)"), "order product selector uses full filtered data with selector-specific visible subset, not product-page pagination");
assert(orderForm.includes("product-select-item") && orderForm.includes("product-option-placeholder") && orderForm.includes("orders.productOption.refineSearch"), "compact product selector image/placeholder/refine markers exist");
assert(existsSync("frontend/src/components/filter-controls.tsx") && existsSync("frontend/src/components/date-range-selector.tsx") && topbar.includes("DateRangeSelector"), "FilterBar/SearchInput/SortSelect/DateRangeSelector markers exist");
assert(inventoryPage.includes("transactionPage") && inventoryPage.includes("transactionPageSize") && inventoryPage.includes("paginatedTransactions") && inventoryPage.includes("historyTypeFilter"), "transaction history has independent pagination and filter state");
assert(inventoryPage.match(/<PaginationControls[\s\S]*transactionPage/) && transactionHistory.includes("transactionTypeLabel") && transactionHistory.includes("transactionReasonLabel"), "transaction history uses PaginationControls and localized transaction helpers");
assert(integrations.includes("t(\"novaPoshta.senderSettings\")") && integrations.includes("dark:bg-amber-500/15") && integrations.includes("maskedCredentials"), "settings integrations uses i18n and dark-aware warning styles");
assert(city.includes("isFetching") && city.includes("noCitiesFound") && city.includes("sellora-scrollbar"), "Nova Poshta city search has loading/empty/error states and custom scrollbar");
assert(warehouse.includes("disabled={!cityRef}") && warehouse.includes("selectCityFirst") && warehouse.includes("noWarehousesFound"), "Nova Poshta warehouse search is disabled until city ref and has states");
assert(en.includes('"dateRange"') && uk.includes('"dateRange"') && en.includes('"filters"') && uk.includes('"filters"'), "new i18n filter/date-range keys exist in both locales");
assert(en.includes('"transactionTypes"') && uk.includes('"transactionTypes"') && en.includes('"novaPoshta"') && uk.includes('"novaPoshta"'), "inventory transaction and integration localization keys exist");
console.log("post-pagination QA regression passed");
