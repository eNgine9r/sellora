import { readFileSync } from "node:fs";

const checks = [
  ["frontend/src/lib/currency.ts", "formatMoney"],
  ["frontend/src/lib/currency.ts", "UAH"],
  ["frontend/src/types/auth.ts", "currency_code"],
  ["frontend/src/app/settings/page.tsx", "Currency controls how financial values are displayed across Sellora. It does not convert historical amounts."],
  ["frontend/src/app/settings/page.tsx", "UAH — Ukrainian hryvnia"],
  ["frontend/src/app/orders/page.tsx", "formatMoney"],
  ["frontend/src/features/orders/components/order-details.tsx", "formatMoney"],
  ["frontend/src/features/orders/components/order-table.tsx", "formatMoney"],
  ["frontend/src/app/dashboard/page.tsx", "formatMoney"],
];

const failures = checks.filter(([file, label]) => !readFileSync(file, "utf8").includes(label));
if (failures.length > 0) {
  console.error("Missing currency formatting labels or wiring:");
  for (const [file, label] of failures) console.error(`- ${file}: ${label}`);
  process.exit(1);
}

console.log(`Currency formatting regression passed (${checks.length} labels checked).`);
