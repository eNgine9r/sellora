import { readFileSync } from "node:fs";

const checks = [
  ["frontend/src/features/orders/components/order-form.tsx", "Add item"],
  ["frontend/src/features/orders/components/order-form.tsx", "Remove item"],
  ["frontend/src/features/orders/components/order-form.tsx", "Price is auto-filled from the selected variant and can be adjusted for discounts."],
  ["frontend/src/features/orders/components/order-form.tsx", "Items subtotal"],
  ["frontend/src/features/orders/components/order-form.tsx", "Estimated profit"],
  ["frontend/src/features/orders/components/order-form.tsx", "Line total"],
  ["frontend/src/features/orders/components/order-form.tsx", "variant?.price"],
  ["frontend/src/features/orders/components/order-form.tsx", "noValidate"],
  ["frontend/src/features/orders/components/order-details.tsx", "Unit price"],
  ["frontend/src/features/orders/components/order-details.tsx", "Line total"],
  ["frontend/src/app/orders/page.tsx", "inventory={inventoryQuery.data ?? []}"],
  ["frontend/src/app/orders/page.tsx", "products={productsQuery.data ?? []}"],
  ["frontend/src/app/orders/page.tsx", "showProfit={currentWorkspace?.role === \"OWNER\"}"],
];

const failures = checks.filter(([file, label]) => !readFileSync(file, "utf8").includes(label));
if (failures.length > 0) {
  console.error("Missing multi-item order labels or wiring:");
  for (const [file, label] of failures) {
    console.error(`- ${file}: ${label}`);
  }
  process.exit(1);
}

console.log(`Multi-item order regression passed (${checks.length} labels checked).`);
