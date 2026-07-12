# Staging Release Checklist — Sprint 8A

Use this checklist with `scripts/staging_release_gate.py` and browser/mobile QA. All data must be synthetic and prefixed with `E2E-8A-<timestamp>`.

## G0 Deployment

- [ ] Frontend staging URL opens over HTTPS.
- [ ] Backend `/health` returns HTTP 200.
- [ ] Login route opens directly.
- [ ] Protected route redirects unauthenticated users safely.
- [ ] Frontend talks to the intended staging API.
- [ ] No Vercel Application Error, Render 502/503, mixed content, or redirect loop.
- [ ] Frontend and backend branch/commit/deploy timestamp are recorded.
- [ ] Repository Alembic head is recorded.
- [ ] Runtime database revision is safely verified or explicitly blocked.

## G1 Authentication/session

- [ ] OWNER login, `/auth/me`, workspace load, session restore and logout pass.
- [ ] MANAGER login and permitted operational routes pass.
- [ ] ANALYST login and read-only restrictions pass.
- [ ] Invalid credentials show a safe error.
- [ ] Browser Back after logout does not restore private state.
- [ ] No token or password appears in UI, logs, or committed artifacts.

## G2 Workspace/team

- [ ] Workspace switcher opens.
- [ ] Switching workspaces changes displayed data.
- [ ] Old workspace drawers/cards/tables disappear.
- [ ] Workspace Settings load.
- [ ] Team users and roles load.
- [ ] Last OWNER protections remain visible/enforced.
- [ ] MANAGER and ANALYST cannot administer team/workspace.

## G3 Dashboard

- [ ] Dashboard loads.
- [ ] Selected period is visible.
- [ ] KPI cards render true zero and unavailable values honestly.
- [ ] Funnel and recent orders render or show truthful empty state.
- [ ] Workspace switch refreshes values.

## G4 Leads/customers

- [ ] Lead list/search/filter load.
- [ ] Synthetic lead create/detail/edit/archive works.
- [ ] Customer list/search load.
- [ ] Synthetic customer create/detail/edit/archive works.
- [ ] No raw enum or UUID is shown.

## G5 Products/inventory

- [ ] Product list/categories/search load.
- [ ] Synthetic product and variant can be created.
- [ ] Inventory record loads for synthetic variant.
- [ ] Controlled stock-in creates a transaction.
- [ ] No negative or impossible quantity is created.

## G6 Orders

- [ ] Synthetic order can be created with synthetic customer and stocked variant.
- [ ] Order detail opens.
- [ ] Revenue/cost/profit state is honest.
- [ ] Inventory reservation behavior is coherent.
- [ ] Payment/status updates work through supported values.
- [ ] Cross-workspace customer/product IDs are rejected.

## G7 Shipments

- [ ] Shipments route loads.
- [ ] Existing or synthetic safe shipment detail opens.
- [ ] Order without shipment shows a truthful state.
- [ ] No real Nova Poshta TTN is created.
- [ ] No API key appears in UI/logs/responses.

## G8 Finance/advertising/analytics/import

- [ ] Finance route loads with no `NaN`/fake zero.
- [ ] Advertising route loads and does not claim live Meta Ads sync.
- [ ] Analytics route loads and period/report states are usable.
- [ ] Import Center route loads and template/download controls do not 404.

## G9 Settings/integrations

- [ ] Settings overview loads.
- [ ] Workspace settings load.
- [ ] Team page loads according to role.
- [ ] Integrations route loads.
- [ ] Nova Poshta and Meta Ads statuses are truthful.
- [ ] Secrets remain masked.

## G10 Mobile/PWA

- [ ] 375×812 viewport smoke passes.
- [ ] 390×844 viewport smoke passes.
- [ ] 430×932 viewport smoke passes.
- [ ] 768×1024 viewport smoke passes.
- [ ] 1366×768 desktop regression passes.
- [ ] Manifest is available and no private API/HTML caching was introduced.

## G11 Network/console/errors

- [ ] No uncaught frontend exceptions.
- [ ] No repeated 401 loop.
- [ ] No unexpected 403/404/500 on core routes.
- [ ] No CORS/hydration errors.
- [ ] No stack traces, SQL, tokens, or secrets in responses/output.
