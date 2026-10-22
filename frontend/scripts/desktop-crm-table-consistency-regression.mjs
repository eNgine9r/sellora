import { readFileSync } from "node:fs";

const read = (path) => readFileSync(path, "utf8");
const tablePaths = {
  leads: "frontend/src/features/leads/components/lead-table.tsx",
  shipments: "frontend/src/features/shipments/components/shipment-table.tsx",
  customers: "frontend/src/features/customers/components/customer-table.tsx",
  orders: "frontend/src/features/orders/components/order-table.tsx",
  products: "frontend/src/features/products/components/product-table.tsx",
  inventory: "frontend/src/features/inventory/components/inventory-table.tsx",
  campaigns: "frontend/src/features/advertising/components/campaign-table.tsx",
  advertisingMetrics: "frontend/src/features/advertising/components/ad-metric-table.tsx",
};
const actions = read("frontend/src/components/ui/row-action-buttons.tsx");
const css = read("frontend/src/app/globals.css");
let passed = 0;

function check(condition, message) {
  if (!condition) throw new Error(`Desktop table consistency: ${message}`);
  passed++;
}

check(actions.includes("IconButton") && actions.includes('variant="ghost"') && actions.includes('variant="danger"'), "standard actions retain edit and archive tones");
check(actions.includes("aria-label") && actions.includes("stopPropagation"), "action icons have accessible labels and do not select their row");
check(css.includes("container-type: inline-size") && css.includes("@container (min-width: 780px)") && css.includes("@container (min-width: 980px)"), "lists switch modes according to actual available container width");

for (const [module, path] of Object.entries(tablePaths)) {
  const source = read(path);
  check(source.includes("RowActionButtons"), `${module}: compact common row actions`);
  check(source.includes("sellora-adaptive-list") && source.includes("sellora-adaptive-table") && source.includes("sellora-adaptive-cards"), `${module}: no-scroll table/card presentation`);
}

const leads = read(tablePaths.leads);
const shipments = read(tablePaths.shipments);
check(leads.includes("lead.instagram_username") && leads.includes("lead.phone") && leads.includes("lead.campaign_name"), "leads contact/source details preserved in merged columns");
check(read(tablePaths.advertisingMetrics).includes("destructiveIcon=\"delete\""), "metric deletion has appropriate destructive icon");
check(shipments.includes("CopyTtnButton") && shipments.includes("shipments.openOrder") && shipments.includes("shipments.createTtn"), "shipment TTN and linked-order actions preserved");
check(!shipments.includes("grid min-w-[160px]") && !leads.includes('className="flex flex-wrap gap-2"'), "old tall desktop button stacks removed");

console.log(`Desktop CRM table consistency passed (${passed} checks).`);
