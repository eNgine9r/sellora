# Demo workspace dataset

Sprint 8B demo data is generated only inside a separate Sellora demo workspace. It is never inserted into a user's real workspace by default.

## Workspace
- Name: `Демо Sellora`
- Slug prefix: `demo-sellora-<safe-generated-suffix>`
- Creator membership: OWNER in the demo workspace only
- External provider calls: 0 Meta calls, 0 Nova Poshta calls
- Demo eligibility: server-side `DEMO_WORKSPACE_CREATE` audit provenance created in the same transaction as the workspace and dataset. Name, slug, and record contents are not accepted as proof that a workspace is demo.

## Core demo scope
The first demo dataset intentionally covers the core operating path:

- CRM: Leads and Customers
- Catalog: Products and Product Variants
- Inventory: Inventory rows and stock-in transactions
- Orders: Orders and Order Items across representative statuses

Synthetic records:

- Leads: six DEMO leads across NEW, IN_PROGRESS, QUALIFIED and CONVERTED states.
- Customers: four DEMO customers with non-routable `+000...` phone placeholders and synthetic Instagram usernames.
- Products/variants: six DEMO products with one active variant each.
- Inventory: stock-in transactions with coherent stock and reserved quantities.
- Orders: five DEMO orders across supported states, with generated order numbers and same-workspace order items.

## Intentionally not seeded

- No shipment drafts and no Nova Poshta TTNs.
- No advertising campaigns or metrics.
- No finance adjustments, refunds, fees, or manual expenses.
- No Meta, Instagram, Nova Poshta, or other provider identifiers.

This is a truthful product decision, not missing data. Shipments and Advertising must show their normal honest empty states in the demo workspace. Finance may display revenue, product cost, and net profit derived from the seeded orders, but it must not imply that manual adjustments or external advertising spend exist.

## Truthfulness labels
UI must show `Демо`, `Синтетичні дані`, and `Не є реальними показниками магазину` when a demo workspace is active.

## Idempotency and rollback
Repeated demo creation returns the active demo workspace proven by the server-side creation audit event. Concurrent duplicate requests are resolved by the deterministic unique slug and a post-conflict provenance lookup, so they do not create multiple active demo workspaces. If generation fails, the service rolls back the transaction instead of leaving a partially usable demo workspace.

## Data safety
Do not copy real customer data, real orders, real phone numbers, real addresses, tokens, provider IDs, or production exports into this dataset.
