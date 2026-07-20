# Weekly Health Blocker Closure — 2026-07-20

## Scope

This closure addresses the actionable code-level findings from the Sellora weekly health report:

- issue #131 — inconsistent Order/Dashboard and Finance net profit;
- issue #132 — orphan active inventory after Product Variant archive;
- issue #137 — unbounded frontend authentication requests during backend outages.

Instagram webhook processing and outbound messaging were reclassified from blocked to runtime-verified based on staging database evidence. Participant username/profile image enrichment remains a separate product enhancement because Meta may not return those fields for every scoped user.

## Canonical net profit

The canonical order and Finance base formula is:

```text
net_profit = revenue
             - product_cost
             - allocated_ad_cost
             - allocated_shipping_cost
             - cod_fee
             - other_order_cost
```

Finance uses the costs stored on included orders so that an order, Dashboard, Analytics, and Finance produce the same base result for the same order set.

Additional Finance adjustments are intentionally applied after the canonical order formula:

- manual expenses;
- refunds;
- discounts;
- fees;
- shipping adjustments.

Advertising campaign spend remains a separate campaign-level metric. When campaign spend differs from the amount allocated to orders, Finance returns a data-quality warning instead of silently replacing the canonical order cost.

Shipment provider cost also remains a comparison source. When it differs from the shipping cost allocated to orders, Finance returns a data-quality warning.

In the existing Finance response contract, `other_expenses` contains `cod_fee + other_order_cost`. The Finance breakdown labels this explicitly.

## Variant and inventory archival

Archiving a Product Variant now follows this transaction contract:

1. resolve the active variant within the requested workspace;
2. lock its active Inventory row;
3. reject the operation when `reserved_quantity > 0`;
4. soft-delete the Product Variant and Inventory row in the same database transaction;
5. retain Inventory Transactions as immutable audit history;
6. write separate audit entries for the variant and inventory archive;
7. commit once.

Archived inventory is excluded from active `/inventory` responses by the existing `deleted_at IS NULL` repository predicate. No direct SQL cleanup is required.

Restoration is intentionally not implicit. The current API treats archive as one-way; a future restore operation must restore the variant and its original inventory row together and validate SKU, identity, reservations, and tenant ownership.

## Authentication outage behavior

Frontend authentication requests now have a bounded timeout of 12 seconds by default. The timeout can be configured with `NEXT_PUBLIC_API_TIMEOUT_MS`, with values below 1000 ms rejected in favor of the safe default.

Behavior:

- HTTP 401 and 422 are shown as invalid credentials;
- backend 5xx responses, network failures, and timeouts are shown as localized server/network errors;
- login, refresh, and current-user requests use the same bounded request helper.

This closes the frontend half of issue #137. Full issue closure still requires runtime evidence for Render `/health`, a valid OWNER login, an invalid-password response, and the protected viewport matrix.
