import { readFileSync } from "node:fs";

const checks = [
  ["frontend/src/components/confirm-action-dialog.tsx", "ConfirmActionDialog"],
  ["frontend/src/features/leads/components/lead-table.tsx", "Archive lead"],
  ["frontend/src/features/customers/components/customer-table.tsx", "Archive customer"],
  ["frontend/src/app/customers/page.tsx", "Archive customer?"],
  ["frontend/src/features/products/components/product-table.tsx", "Archive product"],
  ["frontend/src/app/products/page.tsx", "Archive variant"],
  ["frontend/src/features/orders/components/order-table.tsx", "Archive order"],
  ["frontend/src/app/orders/page.tsx", "Archive test order?"],
  ["frontend/src/features/shipments/components/shipment-table.tsx", "Archive shipment"],
  ["frontend/src/features/advertising/components/campaign-table.tsx", "Archive campaign"],
  ["frontend/src/features/advertising/components/ad-metric-table.tsx", "Delete metric"],
  ["frontend/src/app/inventory/page.tsx", "Adjust stock"],
];

const failures = checks.filter(([file, label]) => !readFileSync(file, "utf8").includes(label));
if (failures.length > 0) {
  console.error("Missing delete/archive labels:");
  for (const [file, label] of failures) {
    console.error(`- ${file}: ${label}`);
  }
  process.exit(1);
}

console.log(`Delete/archive actions regression passed (${checks.length} labels checked).`);
