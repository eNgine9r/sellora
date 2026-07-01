import { readFileSync } from "node:fs";

const checks = [];
const read = (path) => readFileSync(path, "utf8");
const expect = (name, condition) => {
  checks.push({ name, condition });
  if (!condition) {
    throw new Error(`Advertising attribution MVP regression failed: ${name}`);
  }
};

const migration = read("backend/alembic/versions/202607010015_manual_ad_attribution.py");
const leadModel = read("backend/app/models/lead.py");
const orderModel = read("backend/app/models/order.py");
const leadService = read("backend/app/services/lead_service.py");
const orderService = read("backend/app/services/order_service.py");
const leadSchema = read("backend/app/schemas/lead.py");
const orderSchema = read("backend/app/schemas/order.py");
const leadForm = read("frontend/src/features/leads/components/lead-form.tsx");
const orderForm = read("frontend/src/features/orders/components/order-form.tsx");
const leadTable = read("frontend/src/features/leads/components/lead-table.tsx");
const orderDetails = read("frontend/src/features/orders/components/order-details.tsx");
const orderTable = read("frontend/src/features/orders/components/order-table.tsx");
const attributionPanel = read("frontend/src/features/advertising/components/attribution-summary-panel.tsx");
const advertisingPage = read("frontend/src/app/advertising/page.tsx");
const en = read("frontend/src/i18n/messages/en.json");
const uk = read("frontend/src/i18n/messages/uk.json");
const docs = [
  "docs/advertising-metrics.md",
  "docs/pilot-advertising-guide.md",
  "docs/advertising-import-guide.md",
  "docs/meta-ads-integration-plan.md",
  "docs/staging-qa-checklist.md",
  "docs/pilot-qa-checklist.md",
  "docs/mvp-readiness.md",
  "docs/known-limitations.md",
].map(read).join("\n");
const backendTests = ["backend/tests/test_lead_workflow.py", "backend/tests/test_orders.py"].map(read).join("\n");
const frontendSource = [leadForm, orderForm, leadTable, orderDetails, orderTable, attributionPanel, advertisingPage].join("\n");
const allText = [migration, leadModel, orderModel, leadService, orderService, leadSchema, orderSchema, frontendSource, docs, backendTests].join("\n");

expect("lead/order campaign_id migration exists", migration.includes("campaign_id") && migration.includes("leads") && migration.includes("orders"));
expect("campaign foreign keys are nullable and SET NULL", migration.includes("nullable=True") && migration.includes("ondelete=\"SET NULL\""));
expect("lead model exposes campaign relationship and name", leadModel.includes("campaign_id") && leadModel.includes("campaign_name") && leadModel.includes("relationship(\"AdCampaign\")"));
expect("order model exposes campaign relationship and name", orderModel.includes("campaign_id") && orderModel.includes("campaign_name") && orderModel.includes("relationship(\"AdCampaign\")"));
expect("lead/order schemas expose campaign display data", leadSchema.includes("campaign_name") && orderSchema.includes("campaign_name"));
expect("lead service validates workspace campaign link", leadService.includes("AdCampaignRepository") && leadService.includes("Advertising campaign does not exist in this workspace"));
expect("order service validates workspace campaign link", orderService.includes("AdCampaignRepository") && orderService.includes("Advertising campaign does not exist in this workspace"));
expect("cross-workspace campaign tests exist", backendTests.includes("rejects_cross_workspace_campaign_link"));
expect("lead form has optional human-readable campaign selector", leadForm.includes("leads.campaignField") && leadForm.includes("campaign.name") && leadForm.includes("orders.campaignNotSet"));
expect("order form has optional human-readable campaign selector", orderForm.includes("orders.campaignField") && orderForm.includes("campaign.name") && orderForm.includes("orders.campaignNotSet"));
expect("lead/order detail or list display campaign without UUID-only UX", leadTable.includes("campaign_name") && orderDetails.includes("campaign_name") && orderTable.includes("campaign_name"));
expect("advertising page renders manual attribution panel", advertisingPage.includes("AttributionSummaryPanel") && attributionPanel.includes("Manual attribution MVP"));
expect("attribution panel counts attributed orders/revenue/profit and unattributed orders", attributionPanel.includes("attributedOrders") && attributionPanel.includes("attributedRevenue") && attributionPanel.includes("attributedProfit") && attributionPanel.includes("unattributedOrders"));
expect("attribution panel marks manual-only MVP and future Meta attribution", attributionPanel.includes("manual-campaign-attribution") && attributionPanel.includes("Meta Ads API attribution is future work"));
expect("i18n keys for attribution display exist", en.includes("attributionCampaign") && uk.includes("attributionCampaign") && en.includes("campaignNotSet") && uk.includes("campaignNotSet") && en.includes("campaignHelp") && uk.includes("campaignHelp"));
expect("docs explain manual optional workspace-scoped attribution", docs.includes("Manual attribution MVP") && docs.includes("workspace-scoped") && docs.includes("optional"));
expect("docs keep Meta API attribution as future work", docs.includes("future Meta") || docs.includes("Future Meta"));
expect("docs keep advertising import not pilot-ready", docs.includes("not pilot-ready") || docs.includes("not pilot ready"));
expect("no Meta API implementation was introduced", !allText.includes("oauth/callback") && !allText.includes("MetaAccessToken"));
expect("no credential fixture marker", !/(access_token>|refresh_token>|_authToken|Authorization: Bearer)/i.test(allText));

console.log(`Advertising attribution MVP regression passed (${checks.length} checks).`);
