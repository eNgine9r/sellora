import { readFileSync } from "node:fs";

const page = readFileSync("frontend/src/app/settings/import/page.tsx", "utf8");
const panel = readFileSync("frontend/src/features/import-center/components/import-report-panel.tsx", "utf8");
const service = readFileSync("frontend/src/services/import-center.ts", "utf8");

const required = [
  "your_jewelry_orders_history_v1",
  "your_jewelry_advertising_history_v1",
  "affect_inventory",
  "It does not affect current inventory by default.",
  "It does not connect to Meta Ads API.",
  "Historical orders counters",
  "Historical advertising counters",
  "orders_detected",
  "campaigns_detected",
];

for (const needle of required) {
  if (!page.includes(needle) && !panel.includes(needle) && !service.includes(needle)) {
    throw new Error(`Missing historical import UI marker: ${needle}`);
  }
}

console.log("Historical import regression passed");
