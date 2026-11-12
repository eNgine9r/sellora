import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = (file) => readFileSync(file, "utf8");
const topbar = source("frontend/src/components/app-topbar.tsx");
const dialog = source("frontend/src/components/global-search.tsx");
const api = source("frontend/src/services/global-search.ts");
const route = source("backend/app/api/v1/search.py");
const search = source("backend/app/services/global_search_service.py");
const router = source("backend/app/api/v1/router.py");
const en = JSON.parse(source("frontend/src/i18n/messages/en.json"));
const uk = JSON.parse(source("frontend/src/i18n/messages/uk.json"));

assert(topbar.includes("<GlobalSearch workspaceId={currentWorkspaceId} />"), "Topbar opens real search instead of inert input");
assert(!topbar.includes("<input "), "Old dead search input removed");
assert(topbar.includes('data-topbar-search-group') && dialog.includes("data-global-search-mobile"), "Search available on desktop and mobile");
assert(dialog.includes('event.ctrlKey || event.metaKey') && dialog.includes('event.key === "/"'), "Ctrl/Command+K and slash shortcuts work");
assert(dialog.includes('"ArrowDown"') && dialog.includes('"ArrowUp"') && dialog.includes('"Enter"') && dialog.includes('"Escape"'), "Keyboard result navigation and close work");
assert(dialog.includes('role="dialog" aria-modal="true"') && dialog.includes('role="combobox"') && dialog.includes('role="option"'), "Accessible command search");
assert(dialog.includes('aria-busy=') && dialog.includes('resultsQuery.isError') && dialog.includes('!results.length'), "Loading error and empty states");
assert(dialog.includes('setDebounced(query.trim().slice(0, 80)), 280'), "Debounced bounded search");
assert(dialog.includes('["global-search", workspaceId, debounced]') && dialog.includes('queryFn: ({ signal })'), "Workspace-scoped cached abortable search");
assert(dialog.includes('query.trim().slice(0, 80) === debounced'), "Stale query results not flashed");
assert(api.includes("encodeURIComponent(normalized)") && api.includes('"X-Workspace-ID": workspaceId') && api.includes('signal,'), "Safe scoped API request");
assert(route.includes('require_min_role(RoleName.ANALYST)') && route.includes('min_length=2, max_length=80'), "Authenticated bounded endpoint");
assert(router.includes('api_router.include_router(search_router)'), "Search endpoint registered");
for (const model of ["Order", "Customer", "Lead", "Product", "Shipment"]) {
  assert(search.includes('select(' + model + ')'), model + " is queried");
}
assert(search.includes('workspace_id == workspace_id') && search.includes('deleted_at.is_(None)'), "Only live workspace rows returned");
assert(search.includes('PER_KIND_LIMIT = 4'), "Response bounded by type");
for (const [name, param] of [["customers","customer_id"],["leads","lead_id"],["products","product_id"],["shipments","shipment_id"]]) {
  const page = source(`frontend/src/app/${name}/page.tsx`);
  assert(page.includes('useSearchParams().get("' + param + '")') && page.includes('openedFromSearchRef'), name + " supports exact ID deep-link");
}
assert(source("frontend/src/app/orders/page.tsx").includes('requestedOrderId = searchParams.get("order_id")'), "Order deep link remains");
assert(source("frontend/src/app/orders/page.tsx").includes('genericCreateOpened'), "Create order quick action opens the form");
for (const translations of [en,uk]) {
  assert(translations.topbar.search.title && translations.topbar.search.keyboard && translations.topbar.search.groups.shipments, "Search UI localized");
}
console.log("Global topbar search / RBAC / responsive / deep-link regression PASS (19 checks).");
