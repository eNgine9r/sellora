import { existsSync, readdirSync, readFileSync } from "node:fs";

const read = (path) => readFileSync(path, "utf8");
const files = {
  report: read("docs/sprint-8d-orders-inventory-shipments.md"),
  lifecycle: read("docs/order-lifecycle-and-stock-effects.md"),
  inventory: read("docs/inventory-transaction-contract.md"),
  shipment: read("docs/local-shipment-pilot-contract.md"),
  guide: read("docs/pilot-operations-guide.md"),
  release: read("docs/pilot-release-decision.md"),
  orderService: read("backend/app/services/order_service.py"),
  inventoryService: read("backend/app/services/inventory_service.py"),
  shipmentService: read("backend/app/services/shipment_service.py"),
  orderRepo: read("backend/app/repositories/order_repository.py"),
  inventoryRepo: read("backend/app/repositories/inventory_repository.py"),
  shipmentRepo: read("backend/app/repositories/shipment_repository.py"),
  shipmentMigration: read("backend/alembic/versions/202606020009_shipments_engine.py"),
  orderTests: existsSync("backend/tests/orders/test_order_lifecycle_pilot.py") ? read("backend/tests/orders/test_order_lifecycle_pilot.py") : "",
  lockingTests: existsSync("backend/tests/orders/test_sprint_8d_locking_contract.py") ? read("backend/tests/orders/test_sprint_8d_locking_contract.py") : "",
  inventoryTests: existsSync("backend/tests/inventory/test_inventory_operational_invariants.py") ? read("backend/tests/inventory/test_inventory_operational_invariants.py") : "",
  shipmentTests: existsSync("backend/tests/shipments/test_local_shipment_pilot.py") ? read("backend/tests/shipments/test_local_shipment_pilot.py") : "",
  ordersPage: read("frontend/src/app/orders/page.tsx"),
  inventoryPage: read("frontend/src/app/inventory/page.tsx"),
  shipmentsPage: read("frontend/src/app/shipments/page.tsx"),
  uk: read("frontend/src/i18n/messages/uk.json"),
  en: read("frontend/src/i18n/messages/en.json"),
};
const migrationNames = readdirSync("backend/alembic/versions");
const checks = [
  ["Sprint 8D report exists", existsSync("docs/sprint-8d-orders-inventory-shipments.md") && files.report.includes("Existing capability inventory")],
  ["issue #134 disposition exists", /Issue #134 disposition/i.test(files.report + files.inventory) && files.inventoryRepo.includes("ProductVariant.deleted_at.is_(None)")],
  ["reservation, deduction and release semantics documented", /Order creation.*reserved|Order creation/i.test(files.lifecycle) && files.lifecycle.includes("SHIPPED") && files.lifecycle.includes("CANCELLED")],
  ["order edit delta behavior documented", files.lifecycle.includes("Reservation delta") && files.orderService.includes("new_quantities.get(variant_id, 0) - old_quantities.get(variant_id, 0)")],
  ["inventory mutations use PostgreSQL row locks", files.inventoryRepo.includes("def get_for_update") && files.inventoryRepo.includes("def get_by_variant_for_update") && files.inventoryRepo.includes(".with_for_update()") && files.inventoryRepo.includes("populate_existing=True")],
  ["order lifecycle mutations lock order rows", files.orderRepo.includes("def get_for_update") && files.orderRepo.includes(".with_for_update()") && files.orderService.includes("self.orders.get_for_update")],
  ["inventory invariants are enforced", files.inventoryService.includes("stock_quantity < inventory.reserved_quantity") && files.inventoryService.includes("Cannot reserve more than available stock")],
  ["shipment-order-stock mutation shares outer transaction", files.orderService.includes("commit: bool = True") && files.shipmentService.includes("commit=False") && files.shipmentService.includes("self.db.commit()")],
  ["locking contract tests exist", files.lockingTests.includes("test_inventory_mutations_use_postgresql_row_locks") && files.lockingTests.includes("test_shipment_order_inventory_side_effects_share_one_commit_boundary")],
  ["one-active-shipment behavior documented", /one-active-shipment/i.test(files.report + files.shipment) && files.shipmentTests.includes("one_active_shipment")],
  ["one-active-shipment DB constraint exists", files.shipmentMigration.includes("uq_shipments_workspace_active_order") && files.shipmentMigration.includes("status != 'CANCELLED'")],
  ["shipment unique conflicts are safely handled", files.shipmentService.includes("IntegrityError") && files.shipmentService.includes("self.db.rollback()")],
  ["real Nova Poshta calls remain out of scope", /No real Nova Poshta|Nova Poshta.*out of scope|provider calls = 0/i.test(files.report + files.shipment) && !/api\.novaposhta\.ua|NovaPoshtaClient|fetch\([^)]*novaposhta/i.test(files.shipmentService + files.shipmentsPage)],
  ["ANALYST mutation denial remains", /ANALYST/i.test(files.report + files.lifecycle + files.shipment) && /Read-only|mutation.*denied|denied/i.test(files.report + files.lifecycle)],
  ["workspace-switch reset is implemented", files.ordersPage.includes("setEditingOrder(null)") && files.ordersPage.includes("setIsCreateOpen(false)") && files.inventoryPage.includes("setEditingInventory(null)") && files.shipmentsPage.includes("setEditingShipment(null)") && files.shipmentsPage.includes("setInitialOrderId(undefined)")],
  ["duplicate-submit guards remain", /isPending/.test(files.ordersPage) && /isPending/.test(files.inventoryPage) && /isPending/.test(files.shipmentsPage)],
  ["no new migration exists", !migrationNames.some((name) => /8d|orders.*inventory|shipment.*pilot|issue.*134/i.test(name))],
  ["no raw UUID labels introduced", !/(Workspace ID:|Order ID:|Inventory ID:|Shipment ID:|workspace_id:|order_id:|inventory_id:|shipment_id:)/.test(files.ordersPage + files.inventoryPage + files.shipmentsPage)],
  ["backend enums remain English", !/ДОСТАВЛЕНО|СКАСОВАНО|ВІДПРАВЛЕНО|НОВЕ|ПОВЕРНЕНО/.test(read("backend/app/models/order.py") + read("backend/app/models/inventory.py") + read("backend/app/models/shipment.py"))],
  ["Sprint 8C remains approved", /Sprint 8C.*APPROVED|Sprint 8C — APPROVED|Import Center controlled pilot.*GREEN/is.test(files.release)],
  ["controlled pilot remains GREEN", /Controlled guided pilot remains GREEN|Controlled guided pilot.*GREEN/is.test(files.release)],
  ["localized order inventory shipment strings exist", files.uk.includes('"orders"') && files.uk.includes('"inventory"') && files.uk.includes('"shipments"') && files.en.includes('"orders"')],
  ["archived variants cannot be sold", files.orderService.includes("Product variant is archived") && files.orderTests.includes("archived_variant")],
];
const failed = checks.filter(([, ok]) => !ok);
if (failed.length) {
  console.error(`Orders/inventory/shipments pilot regression failed: ${failed.map(([name]) => name).join(", ")}`);
  process.exit(1);
}
console.log(`Orders/inventory/shipments pilot regression passed (${checks.length} checks).`);
