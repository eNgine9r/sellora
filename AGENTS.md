# AGENTS.md — Sellora Development Instructions

This file defines the permanent operating rules for Codex and other AI agents working in the Sellora repository.

Sellora must be developed as a real SaaS product for paying customers, not as a demo admin panel.

---

## 1. Product identity

Sellora is a SaaS CRM/ERP platform for Instagram shops, initially focused on the Ukrainian market.

Main user flow:

```text
Instagram Direct lead → customer → order → payment → shipment → profit → repeat sale
```

Sellora helps Instagram shop owners manage:

- leads from Direct and ads;
- customers and repeat sales;
- orders, payment status, status history, and profit;
- products, variants, prices, and images;
- inventory, reserved quantity, transactions, and low-stock alerts;
- shipments with future Nova Poshta integration;
- advertising spend, messages, leads, orders, ROAS, CPA, CPL, revenue, and net profit;
- finance and analytics;
- imports from historical store data;
- future integrations, automation, and AI insights.

The product must feel like a modern Ukrainian-first SaaS for real Instagram sellers, not like a technical backend dashboard.

---

## 2. Source of truth and priority

When requirements conflict, follow this order:

1. Explicit user request in the current task.
2. This `AGENTS.md` file.
3. Existing architecture and business rules implemented in the repository.
4. Existing UI/UX conventions in the repository.
5. General best practices.

Core accepted decisions:

- Product focus: Instagram shops in Ukraine.
- Architecture: Clean Architecture + Modular Monolith.
- Backend: FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL, Pydantic v2, JWT, RBAC, Pytest.
- Frontend: Next.js, TypeScript, React, SaaS UI, mobile-first UX.
- Multi-tenant workspace isolation from day one.
- Ukrainian is the default MVP UI language.
- English may exist as a secondary language.
- Backend/API enum values remain in English.
- UI localization happens only at the frontend level.
- Business rules matter more than visual CRUD screens.

Do not introduce a new architecture, major dependency, folder structure, or domain concept unless explicitly requested or clearly required by existing code.

---

## 3. Agent behavior

Before changing code:

- inspect the existing repository structure;
- verify frontend and backend locations;
- inspect existing models, schemas, services, repositories, routes, and tests;
- inspect current localization approach;
- inspect current environment variables and scripts;
- reuse existing conventions instead of inventing new ones.

Change discipline:

- keep changes focused;
- avoid large rewrites;
- do not remove working functionality to simplify a task;
- do not rename backend enum values, database columns, API payload fields, or public routes unless explicitly requested;
- do not fake analytics values or business behavior;
- create honest loading, empty, and error states when data is unavailable;
- do not hardcode secrets, tokens, workspace IDs, user IDs, API URLs, or credentials.

Every completed task response must include:

```text
Summary
- ...

Files changed
- ...

Checks run
- ...

Risks / follow-up
- ...
```

Only claim checks were run if they were actually run.

---

## 4. Branch and PR rules

Preferred branch pattern:

```text
codex/{date}-{feature}
```

Examples:

```text
codex/2026-06-08-fix-localization
codex/2026-06-08-dashboard-polish
codex/2026-06-08-orders-product-selector
```

Pull requests should be focused on one sprint task or one related issue group.

Do not mix unrelated backend, frontend, localization, migrations, and styling refactors in one PR unless the task explicitly requires it.

---

## 5. Architecture rules

Sellora follows Clean Architecture + Modular Monolith.

Hard rules:

- Business logic must not depend on FastAPI.
- API routes must stay thin.
- API routes must not contain direct SQLAlchemy queries or business calculations.
- Business logic must live in services.
- Database access must go through repositories.
- Every business entity must be workspace-scoped.
- Every business-data query must filter by `workspace_id`.
- Users must never access another workspace's data.
- RBAC checks must be enforced on the backend.
- Soft delete must be respected where implemented.
- Audit logging must be preserved for critical changes.

Layer responsibilities:

### API layer

Responsible for:

- request validation;
- response serialization;
- authentication and authorization dependency wiring;
- calling service methods.

Must not contain:

- direct DB queries;
- profit calculations;
- inventory calculations;
- order workflow logic;
- lead conversion logic;
- advertising formula logic.

### Service layer

Responsible for:

- workflows;
- domain validation;
- calculations;
- status transitions;
- inventory reservation/deduction/release;
- lead conversion;
- profit calculation;
- shipment creation logic;
- analytics aggregation coordination.

Examples:

```text
OrderService.create_order()
OrderService.update_status()
OrderService.calculate_profit()
OrderService.cancel_order()
LeadService.convert_to_customer()
LeadService.convert_to_order()
InventoryService.reserve_stock()
AdvertisingService.calculate_roas()
```

### Repository layer

Responsible for:

- all database access;
- workspace-scoped queries;
- soft-delete filters;
- persistence operations;
- query optimization.

Repositories must not contain UI logic, HTTP logic, or user-facing copy.

---

## 6. Backend rules

Use the existing backend stack:

- Python 3.12;
- FastAPI;
- SQLAlchemy 2.0;
- Alembic;
- PostgreSQL;
- Pydantic v2;
- JWT;
- Passlib / Argon2 if already used;
- Pytest.

Respect the existing backend structure. Expected structure may include:

```text
backend/
  app/
    core/
    database/
    models/
    schemas/
    repositories/
    services/
    api/
    dependencies/
    middleware/
    auth/
    utils/
  tests/
  alembic/
```

If the actual repository differs, follow the actual repository convention.

Do not change API response contracts unless the frontend and tests are updated accordingly.

Never hardcode:

- database URLs;
- JWT secrets;
- API keys;
- tokens;
- workspace IDs;
- user IDs;
- staging/production URLs.

Expected environment variables may include:

```text
DATABASE_URL
SECRET_KEY
JWT_SECRET
JWT_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
```

---

## 7. Multi-tenant workspace isolation

Workspace isolation is non-negotiable.

Every business entity must contain or be reachable through:

```text
workspace_id
```

Every query reading business data must be scoped to the current workspace.

Business entities include:

- leads;
- customers;
- customer notes;
- customer addresses;
- tags;
- products;
- product variants;
- inventory records;
- inventory transactions;
- orders;
- order items;
- order status history;
- shipments;
- ad campaigns;
- ad metrics;
- expenses;
- notifications;
- insights;
- attachments;
- integration connections.

Avoid unsafe direct lookups like:

```python
order = session.get(Order, order_id)
```

unless followed by strict workspace validation.

Prefer repository methods like:

```python
get_by_id(workspace_id=current_workspace.id, id=order_id)
```

Any change touching workspace scoping, authentication, authorization, or repository filters is high risk and requires careful review.

---

## 8. RBAC rules

Expected roles:

```text
OWNER
MANAGER
ANALYST
```

Expected permission intent:

### OWNER

Full access.

### MANAGER

Operational access to leads, orders, customers, shipments, and inventory operations if allowed by current implementation.

### ANALYST

Read-only access mainly to dashboard, advertising, finance, analytics, and reports.

Frontend hiding of buttons is not enough. Backend must enforce permissions.

---

## 9. Soft delete and audit logging

Business entities should not be permanently deleted unless explicitly requested.

Expected soft-delete fields:

```text
deleted_at
deleted_by
```

Queries should exclude deleted data by default.

Preserve or create audit logs for critical events:

- create;
- update;
- archive/delete;
- restore;
- status change;
- payment status change;
- inventory change;
- profit change;
- role change;
- integration connection change.

Do not remove audit logging to simplify implementation.

---

## 10. Frontend rules

Use the existing frontend stack:

- Next.js;
- TypeScript;
- React;
- existing styling system, likely Tailwind CSS or component-based styling;
- TanStack Query if already used.

Do not introduce Redux unless explicitly requested.

Expected private modules may include:

```text
/overview
/leads
/orders
/customers
/products
/inventory
/advertising
/finance
/analytics
/shipments
/settings
```

Reusable UI components should be preferred where existing:

```text
DataTable
KpiCard
TrendBadge
StatusBadge
PageHeader
DrawerForm
ConfirmDialog
ChartCard
EmptyState
LoadingSkeleton
PaginationControls
```

UX rules:

- Build for real Instagram shop owners, not developers.
- Main workflows must be fast and clear.
- Do not show technical implementation details in user-facing copy.
- Every touched page should have loading, empty, error, and success states where relevant.
- Tables must remain usable on desktop and mobile.
- On mobile, prefer responsive cards or controlled horizontal scrolling.
- Destructive actions must have confirmation.
- Buttons must have clear labels or tooltips.
- Forms must show clear validation errors.

---

## 11. Localization rules

Ukrainian is the default MVP UI language.

English can be supported as a secondary language.

Backend/API enum values must remain English. Do not translate enum values in the database or API.

Correct approach:

```text
DB/API: DELIVERED
UI uk: Доставлено
UI en: Delivered
```

Incorrect approach:

```text
DB/API: ДОСТАВЛЕНО
```

All user-facing text in touched UI must come from localization dictionaries or existing localization helpers when available.

Localize:

- sidebar;
- topbar;
- dashboard cards;
- tables;
- forms;
- buttons;
- filters;
- status badges;
- empty states;
- loading states;
- error messages;
- tooltips;
- modal/drawer copy;
- chart labels;
- date and currency formatting.

Avoid mixed Ukrainian/English UI.

Use Ukrainian-friendly formats where possible:

```text
08.06.2026
520,00 грн
```

or a consistent project-wide alternative.

Explain abbreviations where useful:

```text
ROAS — окупність реклами
CPA — ціна замовлення
CPL — ціна ліда
COD — накладений платіж
TTN — номер накладної
SKU — артикул товару
```

---

## 12. Leads rules

Leads are central for Instagram shops.

A lead may come from:

- Instagram Direct;
- Instagram Ads;
- Facebook;
- Telegram;
- repeat customer;
- manual entry.

Expected lead statuses:

```text
NEW
IN_PROGRESS
QUALIFIED
CONVERTED
LOST
```

Business rules:

- every new potential customer request can become a lead;
- leads may be assigned to managers;
- a lead can convert to a customer;
- a lead can convert to an order;
- when lead is lost, store a reason if current schema supports it;
- preserve lead-to-customer/order relationships;
- update audit logs for key lead actions where supported.

Do not treat leads as a generic contact list. Leads are the first step of the Instagram Direct → profit flow.

---

## 13. Orders rules

Orders are the operational core of Sellora.

Expected order statuses:

```text
NEW
CONFIRMED
SHIPPED
DELIVERED
COMPLETED
RETURNED
CANCELLED
```

Expected payment statuses:

```text
PENDING
PAID
COD
REFUNDED
```

Business rules:

- orders may be created manually or from leads;
- order number should be generated automatically if implemented;
- order items must preserve product/variant relationship and price/cost snapshot if current schema supports it;
- order status changes should create history/audit where supported;
- order detail UI should show customer, phone, status, payment, revenue, profit, products, shipment, and status history where available;
- cancellation and returns must correctly release or restore stock;
- profit must be recalculated when relevant financial fields change.

Do not implement order status changes as simple label edits if they affect inventory, profit, shipment, or customer totals.

---

## 14. Inventory rules

Inventory must support:

- stock quantity;
- reserved quantity;
- inventory transactions;
- low-stock alerts;
- stock increase;
- stock decrease;
- adjustment;
- reservation;
- release;
- return.

Expected transaction types should remain backend enums and be translated in UI:

```text
STOCK_IN → Надходження
STOCK_OUT → Списання
ADJUSTMENT → Коригування
RESERVATION → Резерв
RELEASE → Зняття резерву
RETURN → Повернення
```

Business rules:

- creating an order reserves quantity if the current implementation supports reservation;
- stock is deducted when an order becomes shipped if this is the accepted business rule in current code;
- cancelled orders release reserved quantity;
- returned orders restore stock;
- stock cannot silently go negative unless explicitly supported by business rules;
- every stock movement should create a transaction record.

Inventory logic is high risk. Add or update tests when changing it.

---

## 15. Products and variants rules

Products must support Instagram-shop catalog needs:

- name;
- category;
- images;
- SKU;
- price;
- cost;
- variants;
- status/archive;
- inventory relation.

Variants may include:

- color;
- size;
- SKU;
- barcode;
- price;
- cost;
- status.

Rules:

- do not duplicate variants with the same meaningful attributes if uniqueness rules exist;
- product and variant selectors in orders must show enough information to choose correctly;
- product lists and variant lists must be paginated when large;
- action buttons must not be clipped on desktop or mobile;
- product import must preserve SKU/variant relationships.

---

## 16. Advertising and analytics rules

Advertising is a key Sellora module because Instagram shops depend heavily on Meta ads.

Track where supported:

- spend;
- impressions;
- reach;
- clicks;
- messages;
- leads;
- orders;
- revenue;
- net profit;
- ROAS;
- CPA;
- CPL.

Formulas:

```text
ROAS = revenue / ad_spend
CPA = ad_spend / orders_count
CPL = ad_spend / leads_count
AOV = revenue / orders_count
Net profit = revenue - product_cost - ad_cost - shipping_cost - cod_fee - other_cost
```

If denominator is zero, return `null`, `—`, or a clearly handled empty value. Do not return misleading infinity or fake zero unless current business logic explicitly requires it.

Analytics UI rules:

- always show the selected period;
- explain or imply the data source;
- avoid mismatch between summary cards and detailed tables;
- chart labels must be localized;
- empty states must explain how to add/import data.

---

## 17. Dashboard rules

Dashboard must answer quickly:

1. How much did the shop earn?
2. How much was spent on ads?
3. How many orders were received?
4. Which products perform best?
5. What needs attention?

Core dashboard areas:

- Revenue;
- Profit;
- Orders;
- ROAS;
- CPA/CPL where relevant;
- Lead funnel;
- Sales/profit trend;
- Recent orders;
- Top products;
- Alerts/insights.

Every KPI must have a clear period such as:

```text
Сьогодні
Останні 7 днів
Останні 30 днів
Поточний місяць
Увесь період
```

Do not show historical tables beside zero KPI values without explaining the period difference.

---

## 18. Shipments rules

Shipments must be compatible with future Nova Poshta integration.

Expected shipment data may include:

- order relation;
- tracking number / TTN;
- recipient name;
- phone;
- city;
- warehouse/branch;
- status;
- cost;
- created date;
- delivered date.

Expected future statuses:

```text
CREATED
IN_TRANSIT
DELIVERED
RETURNED
```

MVP limitation may be one shipment per order unless current code supports more.

Do not hardcode Nova Poshta credentials. Use integration connections and environment/secret handling.

---

## 19. Finance rules

Finance must be practical for small Instagram shops.

Track where supported:

- revenue;
- product cost;
- advertising cost;
- shipping cost;
- COD fee;
- other expenses;
- net profit;
- margin.

Formula:

```text
net_profit = revenue - product_cost - ad_cost - shipping_cost - cod_fee - other_cost
```

Do not mix revenue and profit. Do not show profit if required costs are missing unless the UI clearly explains it as estimated or incomplete.

---

## 20. Import rules

Sellora must support historical imports from spreadsheets.

Import flows should support:

- products;
- variants;
- customers;
- orders;
- inventory;
- advertising metrics;
- expenses where relevant.

Rules:

- validate before writing;
- support dry-run/preview when current import architecture supports it;
- show row-level errors;
- do not partially mutate data without clear reporting;
- preserve workspace isolation;
- avoid duplicate customers/products where matching rules exist;
- do not silently ignore unknown columns.

Excel parsing may use `openpyxl` if already used.

---

## 21. Integrations rules

Future integrations include:

- Instagram Graph API;
- Meta Ads API;
- Nova Poshta;
- Telegram;
- payment providers;
- AI insights.

Rules:

- store external tokens only encrypted;
- never log raw tokens;
- keep provider-specific logic isolated;
- do not place integration logic directly in UI components;
- design connections per workspace;
- sync failures should create clear errors/notifications when supported.

Do not implement half-integrations with hardcoded tokens or temporary provider logic in random modules.

---

## 22. Notifications and insights rules

Notifications may be created for:

- low stock;
- order returned;
- high CPA;
- integration failure;
- import failure;
- important shipment status.

Insights may include:

- best-selling product;
- highest ROAS campaign;
- low conversion issue;
- low-stock risk;
- repeat-customer opportunity.

Notifications and insights should be workspace-scoped and not hardcoded.

---

## 23. Staging and deployment rules

Current staging concept:

```text
Vercel frontend
↓
Render backend
↓
Supabase PostgreSQL database
```

Do not hardcode staging URLs in application logic.

Use environment variables.

Never expose:

- access tokens;
- refresh tokens;
- passwords;
- full database URLs;
- JWT secrets;
- provider tokens.

Avoid logging secrets in console output.

Preserve backend health/docs availability where implemented:

```text
/health
/docs
```

---

## 24. Known QA priorities

Current staging state is technically functional, but MVP polish is still needed.

When touching related areas, actively avoid or fix these issue groups:

### Localization

- mixed Ukrainian/English UI;
- raw enum values visible in UI;
- untranslated dashboard sections;
- untranslated advertising tables;
- untranslated product variant headers;
- English empty states.

### Analytics clarity

- dashboard KPI period unclear;
- advertising summary not matching daily metrics;
- ROAS/CPA/CPL without period or formula context;
- zero KPI values beside historical data without explanation.

### Loading and empty states

- showing “not found” before data finishes loading;
- empty states without next action;
- filtered empty state not separated from true empty state;
- missing error messages.

### Tables and responsive UX

- action buttons clipped;
- heavy horizontal scroll;
- poor mobile usability;
- product selector card spacing too large;
- long lists without pagination.

### UX clarity

- technical login copy;
- unclear topbar plus button;
- unexplained abbreviations;
- disabled-state problems.

---

## 25. Testing rules

Backend tests use Pytest.

Prioritize tests for:

- workspace isolation;
- RBAC;
- authentication;
- lead conversion;
- order creation;
- order status changes;
- inventory reservation/deduction/release;
- profit calculations;
- advertising formulas;
- import validation;
- repository filters;
- soft delete behavior.

Coverage target where realistic:

```text
80%+
```

Frontend checks should use existing project scripts. Likely examples:

```text
npm run lint
npm run typecheck
npm run build
npm test
```

Manual QA checklist for touched UI:

- desktop layout;
- mobile layout;
- loading state;
- empty state;
- error state;
- main action;
- localization;
- status badges;
- permissions if relevant;
- data refresh after mutation;
- no obvious console/runtime errors if checked.

---

## 26. Database and migration rules

Use Alembic for schema changes.

Do not edit staging/production database manually as a substitute for migrations.

Before adding migrations:

- inspect existing models;
- inspect existing migration history;
- preserve existing data;
- use nullable/default strategy where needed;
- add indexes for frequently filtered fields;
- include workspace indexes where relevant.

Common workspace indexes to consider:

```text
workspace_id
workspace_id + created_at
workspace_id + status
workspace_id + deleted_at
workspace_id + customer_id
workspace_id + order_id
```

Do not add excessive indexes without reason.

---

## 27. Performance rules

MVP performance targets where realistic:

```text
Dashboard load: < 2 seconds
Orders list: < 1 second
Customer search: < 500 ms
```

Avoid loading huge datasets into the frontend without pagination/search.

Use pagination for:

- products;
- orders;
- customers;
- inventory transactions;
- advertising metrics;
- variants if the list can grow.

Keep list rendering efficient.

---

## 28. Accessibility and UX quality

Use accessible form labels, buttons, and focus states.

Do not rely only on color to communicate status.

Destructive actions must require confirmation.

Buttons must have clear labels or tooltips.

Forms must show validation messages near fields or in a clear summary.

Empty states should provide a useful next action, for example:

```text
Створити товар
Імпортувати товари
Створити замовлення
Додати рекламну метрику
Створити відправлення
```

---

## 29. Visual design direction

Sellora should look like a modern SaaS, not a raw admin template.

Design should feel:

- clean;
- modern;
- clear;
- commercially trustworthy;
- friendly for small shop owners;
- mobile-ready.

Use cards, tables, badges, drawers, charts, and empty states consistently.

When showing metrics, prioritize clarity over decoration.

---

## 30. Future roadmap awareness

Do not implement future roadmap items unless explicitly requested, but keep architecture compatible with them.

Planned stages:

```text
Dashboard & Analytics: Sprint 2.3–2.5
Data Import & Migration: Sprint 2.6–2.8
Nova Poshta Integration: 3.x
Advertising Integration: 4.x
Finance & Advanced Analytics: 5.x
Automation & Notifications: 6.x
Mobile UX / PWA: 7.x
SaaS Readiness: 8.x
AI Features: 9.x
Release Candidate: 10.x
```

Current task should not accidentally implement half of a future integration in an unstable way.

Good:

- add clean provider fields and encrypted credential structure when requested.

Bad:

- hardcode Meta token handling in a random advertising component.

---

## 31. High-risk areas

Treat these areas as high risk:

- authentication;
- JWT refresh logic;
- RBAC;
- workspace isolation;
- database migrations;
- order status transitions;
- inventory reservation/deduction;
- order cancellation/return logic;
- profit calculation;
- advertising formulas;
- imports that mutate many rows;
- integration credentials;
- soft delete and restore logic;
- audit logging;
- payment-related fields;
- shipment status sync.

For high-risk changes, add or update tests.

---

## 32. Code review checklist

When reviewing Sellora code, check:

### Security

- Are all business queries workspace-scoped?
- Are RBAC checks enforced on backend?
- Are secrets/tokens avoided in code and logs?
- Are integration credentials encrypted?
- Are unsafe direct database lookups avoided?

### Architecture

- Is business logic in services?
- Are DB operations in repositories?
- Are API routes thin?
- Are schemas/models/services consistent?
- Are migrations included for schema changes?

### Business logic

- Is inventory reservation/deduction correct?
- Are order status transitions safe?
- Is profit calculated correctly?
- Are ROAS/CPA/CPL formulas correct?
- Are lead conversions preserving relationships?
- Are customer totals updated only when appropriate?

### Frontend

- Are texts localized?
- Are raw enum values hidden?
- Are loading/empty/error states handled?
- Does the page work on mobile?
- Are table actions visible and usable?
- Are forms validated?
- Are API errors shown clearly?

### Product UX

- Would a real Instagram shop owner understand this?
- Does the UI explain what to do next?
- Are technical terms explained?
- Are dashboard periods and formulas clear?

### Tests

- Were relevant tests added or updated?
- Were checks actually run?
- Are failures documented honestly?

---

## 33. Forbidden shortcuts

Do not:

- disable tests to pass a task;
- remove RBAC checks;
- remove workspace filters;
- convert backend enums to Ukrainian;
- hardcode workspace/user IDs;
- hardcode API URLs;
- hardcode secrets;
- fake analytics numbers;
- hide errors without handling them;
- replace service/repository architecture with inline API logic;
- introduce major dependencies without need;
- rewrite large areas unrelated to the task;
- break staging deployment assumptions;
- show raw provider tokens or JWTs in UI/logs.

---

## 34. Preferred implementation style

### TypeScript

- Keep types strict.
- Avoid `any` unless unavoidable.
- Reuse existing shared types.
- Keep API payload types aligned with backend schemas.

### Python

- Use type hints.
- Keep service methods readable.
- Keep repository methods focused.
- Raise meaningful domain exceptions where existing patterns support them.
- Do not swallow exceptions silently.

### UI copy

For Ukrainian UI, use clear product language.

Prefer:

```text
Створити замовлення
Додати товар
Імпортувати дані
Оберіть замовлення, щоб переглянути деталі
Рухів складу ще немає
```

Avoid:

```text
Create entity
Submit mutation
No records found
Manual panel
```

---

## 35. Definition of Done

A task is done only when:

- implementation matches the requested scope;
- architecture rules are respected;
- workspace isolation is preserved;
- RBAC is not bypassed;
- UI is localized where touched;
- loading/empty/error states are handled where relevant;
- mobile behavior is considered where relevant;
- business rules are not broken;
- tests/checks are run when possible;
- changed files are summarized;
- risks/follow-ups are documented.

For backend tasks, additionally:

- migrations are included if schema changed;
- services/repositories are used properly;
- tests cover changed business logic where practical.

For frontend tasks, additionally:

- no mixed UA/EN text in touched Ukrainian UI;
- raw enum values are translated at UI level;
- user-facing copy is clear for non-technical users;
- forms and tables remain usable on mobile.

---

## 36. Final product standard

Sellora should be built as if it will be used by paying customers.

Every change should move the product closer to this standard:

```text
A reliable, clear, Ukrainian-first SaaS CRM/ERP for Instagram shops that helps owners turn Direct messages into paid orders, shipped parcels, profit, and repeat customers.
```

When uncertain, choose the solution that protects:

1. tenant security;
2. business correctness;
3. user trust;
4. maintainable architecture;
5. fast and simple MVP workflows.
