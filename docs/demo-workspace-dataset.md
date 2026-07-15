# Demo workspace dataset

Sprint 8B demo data is generated only inside a separate Sellora demo workspace. It is never inserted into a user's real workspace by default.

## Workspace
- Name: `Демо Sellora`
- Slug prefix: `demo-sellora-<safe-generated-suffix>`
- Creator membership: OWNER in the demo workspace only
- External provider calls: 0 Meta calls, 0 Nova Poshta calls

## Synthetic records
- Leads: six DEMO leads across NEW, IN_PROGRESS, QUALIFIED and CONVERTED states.
- Customers: four DEMO customers with non-routable `+000...` phone placeholders and synthetic Instagram usernames.
- Products/variants: six DEMO products with one active variant each.
- Inventory: stock-in transactions with coherent stock and reserved quantities.
- Orders: five DEMO orders across supported states, with generated order numbers and same-workspace order items.

## Truthfulness labels
UI must show `Демо`, `Синтетичні дані`, and `Не є реальними показниками магазину` when a demo workspace is active.

## Idempotency and rollback
Repeated demo creation returns the active demo workspace. If generation fails, the service rolls back the transaction instead of leaving a partially usable demo workspace.

## Data safety
Do not copy real customer data, real orders, real phone numbers, real addresses, tokens, provider IDs, or production exports into this dataset.
