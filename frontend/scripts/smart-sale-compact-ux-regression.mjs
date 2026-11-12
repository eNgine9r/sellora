import { readFileSync } from "node:fs";
import { join } from "node:path";
const root = process.cwd();
const read = (file) => readFileSync(join(root, file), "utf8");
const failures = [];
const has = (path, marker) => { if (!read(path).includes(marker)) failures.push(`Missing ${marker} in ${path}`); };
const count = (s, needle) => s.split(needle).length - 1;

const index = "frontend/src/features/shipments/components/nova-poshta-external-inbox.tsx";
const review = "frontend/src/features/shipments/components/smart-sale-approval.tsx";
const route = "frontend/src/app/shipments/confirmations/page.tsx";
const shipments = "frontend/src/app/shipments/page.tsx";
const topbar = "frontend/src/components/app-topbar.tsx";
const api = "frontend/src/services/smart-sale.ts";

has(route, 'mode="full"');
has(route, 'role={currentWorkspace?.role}');
has(shipments, 'mode="summary"');
has(index, 'href="/shipments/confirmations"');
has(index, 'data-smart-sale-compact-list');
has(index, 'data-smart-sale-selected-panel');
has(index, 'data-smart-sale-list-row');
has(index, 'data-sale-queue-counts');
has(index, 'activeFilter === "priced"');
has(index, 'activeFilter === "unmatched"');
has(index, 'setSelectedId(nextCandidate?.document.id ?? null)');
has(index, 'drafts[selected.document.id] ?? {}');
has(index, 'onDraftChange={patch => updateDraft(selected.document.id, patch)}');
has(index, 'scrollIntoView({ behavior: "smooth", block: "start" })');
has(index, 'aria-current={active ? "true" : undefined}');
has(index, 'aria-pressed={activeFilter === value}');
has(topbar, '/shipments/confirmations');
has(topbar, 'encodeURIComponent(sale.document_id)');

const list = read(index);
if (list.includes('max-h-[30rem]')) failures.push("Nested 30rem scrolling queue returned");
if (count(list, "<SmartSaleApproval ") !== 1) failures.push("Expected one selected review panel, not one form per TTN");
if (list.includes('query.data.map((item) =>') && list.includes('<SmartSaleApproval')) failures.push("Old per-row form rendering remains");
if (list.includes('overflow-y-auto pr-1')) failures.push("Nested list scrollbar reintroduced");

has(review, 'data-smart-sale-product-options');
has(review, 'data-sale-selected-product');
has(review, 'data-smart-sale-price-hints');
has(review, 'data-confirm-smart-sale');
has(review, 'min-h-11');
has(review, 'Number.isInteger(qty)');
has(review, 'stockOk');
has(review, 'priceValid');
has(review, 'candidate.reason !== "DIRECT_ALREADY_HAS_ORDER"');
has(review, 'item?.suggested_unit_price');
has(review, 'quotes.length === 1');
has(review, 'onDraftChange({price: q.unit_price})');
has(review, 'onConfirmed?.(result.order_id)');

const reviewSource = read(review);
if (count(reviewSource, 'confirmSmartSale(') !== 1) failures.push("Confirm action must still use the guarded backend API exactly once");
has(api, 'receipt_checked_in_direct: true');
has(api, 'funds_received_in_bank: true');
has(api, 'details_reviewed: true');
has(api, 'expected_conversation_id: conversationId');

if (failures.length) {
  console.error("SMART_SALE_COMPACT_UX_REGRESSION_FAILED\n"+failures.join("\n"));
  process.exit(1);
}
console.log("SMART_SALE_COMPACT_UX_REGRESSION_PASS");
