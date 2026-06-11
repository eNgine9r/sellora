import { readFileSync } from "node:fs";

const checks = [
  ["frontend/src/app/orders/page.tsx", "Edit order"],
  ["frontend/src/app/orders/page.tsx", "lockedItems={!ITEM_EDIT_STATUSES.includes(editingOrder.status)}"],
  ["frontend/src/features/orders/components/order-form.tsx", "initialOrder"],
  ["frontend/src/app/orders/page.tsx", "Save order"],
  ["frontend/src/features/orders/components/order-form.tsx", "Items are locked because this order has already entered shipment workflow."],
  ["frontend/src/features/orders/components/order-form.tsx", "Add item"],
  ["frontend/src/features/orders/components/order-form.tsx", "Remove item"],
  ["frontend/src/features/orders/components/order-form.tsx", "formatMoney"],
];

const failures = checks.filter(([file, label]) => !readFileSync(file, "utf8").includes(label));
if (failures.length > 0) {
  console.error("Missing order edit item labels or wiring:");
  for (const [file, label] of failures) console.error(`- ${file}: ${label}`);
  process.exit(1);
}

console.log(`Order edit items regression passed (${checks.length} labels checked).`);
