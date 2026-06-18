# Sellora Pre-MVP Release Checklist

Use this before inviting external pilot stores. Mark each item with one status: `[ ] Ready`, `[ ] Needs fix`, `[ ] Not in MVP`.

## Deployment and access

- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Frontend deploys to Vercel.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Backend deploys to Render.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Database runs on Supabase PostgreSQL.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Login and token refresh work.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Workspace isolation is validated.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — RBAC hides restricted financial/admin actions.

## Core product flows

- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Dashboard loads real/demo data and no NaN/Infinity appears.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Analytics reports work for sales, products, advertising, customers, inventory and insights.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Orders can be created, edited, status-changed and reviewed.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Products, variants and categories are usable.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Inventory states are understandable.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Customers and leads support pilot flows.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Shipments and Nova Poshta settings are clear.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Advertising manual metrics are usable.

## Imports, demo and onboarding

- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Product catalog import dry-run is understandable.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Historical order import preserves analytics-safe data.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Advertising import updates reports.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Demo seed is idempotent and synthetic.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Demo workspace notice appears only in demo workspace.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — First-run onboarding checklist is visible and mobile-safe.

## Feedback and support

- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Feedback button opens form.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Privacy hint is visible.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Feedback submit loading/success/error states work.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Owner/manager feedback review is workspace-scoped.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Known limitations are documented.

## Mobile, localization and privacy

- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — 375px/390px/430px/768px mobile checks pass for critical pages.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Ukrainian and English labels are present.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Backend enum values remain English.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Security/private-data scans have no new secrets.
- [ ] Ready / [ ] Needs fix / [ ] Not in MVP — Backup/rollback owner is assigned before pilot changes.
