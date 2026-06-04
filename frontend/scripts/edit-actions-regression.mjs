import { readFileSync } from "node:fs";

const checks = [
  ["frontend/src/features/leads/components/lead-table.tsx", "Edit lead"],
  ["frontend/src/features/customers/components/customer-table.tsx", "Edit customer"],
  ["frontend/src/app/customers/page.tsx", "Edit customer"],
  ["frontend/src/features/products/components/product-table.tsx", "Edit product"],
  ["frontend/src/app/products/page.tsx", "Manage product variants"],
  ["frontend/src/app/products/page.tsx", "Edit variant"],
  ["frontend/src/features/products/components/product-variant-form.tsx", "Create a product first before adding variants."],
  ["frontend/src/app/inventory/page.tsx", "Adjust stock"],
  ["frontend/src/features/inventory/components/inventory-table.tsx", "Edit thresholds"],
  ["frontend/src/features/orders/components/order-table.tsx", "Edit order"],
  ["frontend/src/features/orders/components/order-form.tsx", "Create a product variant first before creating an order."],
  ["frontend/src/features/shipments/components/shipment-table.tsx", "Edit shipment"],
  ["frontend/src/features/advertising/components/campaign-table.tsx", "Edit campaign"],
  ["frontend/src/features/advertising/components/ad-metric-table.tsx", "Edit metric"],
  ["frontend/src/features/advertising/components/ad-metric-form.tsx", "Create an advertising campaign first."],
];

const failures = checks.filter(([file, label]) => !readFileSync(file, "utf8").includes(label));
if (failures.length > 0) {
  console.error("Missing edit discoverability labels:");
  for (const [file, label] of failures) {
    console.error(`- ${file}: ${label}`);
  }
  process.exit(1);
}

console.log(`Edit actions regression passed (${checks.length} labels checked).`);
