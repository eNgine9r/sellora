import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = (rel) => fs.readFileSync(path.join(root, rel), "utf8");
const exists = (rel) => fs.existsSync(path.join(root, rel));
const reportPath = "docs/sprint-7b-core-flow-ux-stabilization.md";
const report = exists(reportPath) ? read(reportPath) : "";
const uk = read("frontend/src/i18n/messages/uk.json");
const leadsPage = read("frontend/src/app/leads/page.tsx");
const customersPage = read("frontend/src/app/customers/page.tsx");
const ordersPage = read("frontend/src/app/orders/page.tsx");
const orderDetails = read("frontend/src/features/orders/components/order-details.tsx");
const shipmentsPage = read("frontend/src/app/shipments/page.tsx");
const dashboardPage = read("frontend/src/app/dashboard/page.tsx");
const migrationFiles = fs.readdirSync(path.join(root, "backend/alembic/versions"));

const checks = [
  ["core flow QA report exists", exists(reportPath)],
  ["leads loading/empty/error copy exists", uk.includes("Завантаження лідів") && uk.includes("Лідів ще немає") && leadsPage.includes("leads.loadError")],
  ["customers loading/empty/error copy exists", uk.includes("Завантаження клієнтів") && uk.includes("Клієнтів ще немає") && customersPage.includes("customers.loadError")],
  ["orders loading/empty/error copy exists", uk.includes("Завантаження замовлень") && uk.includes("Замовлень ще немає") && ordersPage.includes("orders.loadError")],
  ["order detail business labels exist", orderDetails.includes("orders.profitNotCalculated") && orderDetails.includes("orders.paymentHint") && orderDetails.includes("orders.shipmentMissing")],
  ["payment status translations exist", uk.includes("Очікує оплату") && uk.includes("Оплачено") && uk.includes("Накладений платіж") && uk.includes("Повернено")],
  ["shipment empty/status/error copy exists", uk.includes("Відправлень ще немає") && shipmentsPage.includes("shipments.loadError")],
  ["dashboard period helper copy exists", uk.includes("Показники рахуються за вибраний період") && dashboardPage.includes("dashboard.periodHelper")],
  ["mobile/core flow notes exist", report.includes("375px") && report.includes("Lead → Customer → Order")],
  ["no Meta-specific feature work was added", report.includes("No Meta features") && !/Meta OAuth changes added|scheduled sync added|apply-sync added/i.test(report)],
  ["no new Sprint 7B migration file was added", migrationFiles.every((file) => !/7b|core_flow|ux_stabilization/i.test(file)) && report.includes("No database migration was added")],
];

let failed = false;
for (const [label, ok] of checks) {
  if (ok) console.log(`OK ${label}`);
  else {
    console.error(`FAIL ${label}`);
    failed = true;
  }
}
if (failed) process.exit(1);
