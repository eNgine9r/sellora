import { readFileSync } from "node:fs";

const checks = [];
function file(path) { return readFileSync(new URL(`../${path}`, import.meta.url), "utf8"); }
function check(name, condition) { checks.push({ name, condition }); }

const inventoryPage = file("src/app/inventory/page.tsx");
const shipmentsPage = file("src/app/shipments/page.tsx");
const inventoryTable = file("src/features/inventory/components/inventory-table.tsx");
const shipmentTable = file("src/features/shipments/components/shipment-table.tsx");
const workspace = file("src/components/crm-workspace.tsx");
const en = file("src/i18n/messages/en.json");
const uk = file("src/i18n/messages/uk.json");

check("/inventory uses route-level WorkspaceSplitView", inventoryPage.includes("<WorkspaceSplitView") && inventoryPage.includes("panelOpen={Boolean(selectedInventory)}"));
check("/shipments uses route-level WorkspaceSplitView", shipmentsPage.includes("<WorkspaceSplitView") && shipmentsPage.includes("panelOpen={Boolean(selectedShipment)}"));
check("inventory uses embedded EntitySidePanel", inventoryPage.includes("<EntitySidePanel") && inventoryPage.indexOf("<EntitySidePanel") < inventoryPage.indexOf("<InventoryTable"));
check("shipments uses embedded EntitySidePanel", shipmentsPage.includes("<EntitySidePanel") && shipmentsPage.indexOf("<EntitySidePanel") < shipmentsPage.indexOf("<ShipmentTable"));
check("Inventory five-card summary is explicit", inventoryPage.includes("<CompactSummary layout=\"five-balanced\""));
check("Shipments five-card summary is explicit", shipmentsPage.includes("<CompactSummary layout=\"five-balanced\""));
check("Inventory separates physical reserved available", inventoryPage.includes("stock_quantity") && inventoryPage.includes("reserved_quantity") && inventoryPage.includes("availableQuantity"));
check("Inventory table exposes selected state", inventoryTable.includes("selectedInventoryId") && inventoryTable.includes("bg-surface-selected"));
check("Shipment table exposes selected state", shipmentTable.includes("selectedShipmentId") && shipmentTable.includes("bg-surface-selected"));
check("Inventory pagination is below the list", inventoryPage.indexOf("<InventoryTable") < inventoryPage.indexOf("<PaginationControls page={inventoryPage}"));
check("Shipments pagination is below the list", shipmentsPage.indexOf("<ShipmentTable") < shipmentsPage.indexOf("<PaginationControls page={page}"));
check("Desktop EntitySidePanel is non-modal aside", workspace.includes('data-entity-side-panel="desktop"') && !workspace.includes('aria-modal="true"'));
check("Mobile EntitySidePanel fallback still uses Drawer", workspace.includes("<Drawer open={open}"));
check("Inventory avoids centered max-width workspace", !inventoryPage.includes("max-w-7xl") && !inventoryPage.includes("bg-[#F8F7FC]"));
check("Shipments avoids old analytics card shell", !shipmentsPage.includes("AnalyticsKpiCard") && !shipmentsPage.includes("selectPrompt"));
check("Shipments does not claim live integration", !shipmentsPage.toLowerCase().includes("live tracking") && !shipmentsPage.toLowerCase().includes("synchronized"));
check("Dd.5 localization exists", en.includes('"summary"') && uk.includes('"summary"') && en.includes('"Available"') && uk.includes('"Доступно"'));

const failed = checks.filter((item) => !item.condition);
if (failed.length) {
  console.error("Sprint Dd.5 regression failed:");
  for (const item of failed) console.error(`- ${item.name}`);
  process.exit(1);
}
console.log(`Sprint Dd.5 regression passed (${checks.length} checks).`);
