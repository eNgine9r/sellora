import fs from "node:fs";

const read = (path) => fs.readFileSync(path, "utf8");
const checks = [];
function expect(name, condition) {
  checks.push({ name, condition });
}

const migration = read("backend/alembic/versions/202607010015_manual_ad_attribution.py");
const leadModel = read("backend/app/models/lead.py");
const orderModel = read("backend/app/models/order.py");
const leadService = read("backend/app/services/lead_service.py");
const orderService = read("backend/app/services/order_service.py");
const leadForm = read("frontend/src/features/leads/components/lead-form.tsx");
const leadsPage = read("frontend/src/app/leads/page.tsx");
const orderForm = read("frontend/src/features/orders/components/order-form.tsx");
const leadTable = read("frontend/src/features/leads/components/lead-table.tsx");
const orderTable = read("frontend/src/features/orders/components/order-table.tsx");
const orderDetails = read("frontend/src/features/orders/components/order-details.tsx");
const uk = read("frontend/src/i18n/messages/uk.json");
const en = read("frontend/src/i18n/messages/en.json");
const validationDoc = read("docs/sprint-4-4-1-attribution-validation.md");

expect("migration adds nullable lead/order campaign columns", migration.includes('"leads"') && migration.includes('"orders"') && migration.includes('"campaign_id"') && migration.includes("nullable=True"));
expect("migration creates indexes and set-null foreign keys", migration.includes("ix_leads_campaign_id") && migration.includes("ix_orders_campaign_id") && migration.includes('ondelete="SET NULL"'));
expect("models expose campaign relationships and names", leadModel.includes("campaign_name") && orderModel.includes("campaign_name") && leadModel.includes('relationship("AdCampaign"') && orderModel.includes('relationship("AdCampaign"'));
expect("services validate campaign through workspace-scoped repository", leadService.includes("self.campaigns.get(workspace_id, campaign_id)") && orderService.includes("self.campaigns.get(workspace_id, campaign_id)"));
expect("forms use campaign selectors with name/platform labels", leadForm.includes("campaigns.map") && orderForm.includes("campaigns.map") && orderForm.includes("campaign.platform") && leadForm.includes("campaign.platform"));
expect("lead edit attribution uses campaign options instead of raw UUID entry", leadsPage.includes("name: \"campaign_id\"") && leadsPage.includes("campaign.name") && leadsPage.includes("campaign.platform") && leadsPage.includes("leads.noCampaign"));
expect("lead/order display uses campaign_name with safe dash fallback", leadTable.includes("lead.campaign_name ?? \"—\"") && orderTable.includes("order.campaign_name ?? \"—\"") && orderDetails.includes("order.campaign_name ?? \"—\""));
expect("Ukrainian and English helper text exists", uk.includes("Необов’язково. Вкажіть кампанію") && uk.includes("Допомагає зрозуміти") && en.includes("Optional. Choose a campaign") && en.includes("Optional. Helps understand"));
expect("validation report documents remaining blockers", validationDoc.includes("CONDITIONALLY APPROVED") && validationDoc.includes("Advertising import remains not pilot-ready"));

const failed = checks.filter((check) => !check.condition);
if (failed.length) {
  console.error("Advertising attribution MVP regression failed:");
  for (const check of failed) console.error(`- ${check.name}`);
  process.exit(1);
}
console.log(`Advertising attribution MVP regression passed (${checks.length} checks).`);
