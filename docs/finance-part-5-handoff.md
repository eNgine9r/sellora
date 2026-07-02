# Finance Part 5 Handoff — Advertising Dependencies

Sprint 4.14 freezes Advertising 4.x and hands off to Part 5 — Finance & Advanced Analytics.

Advertising status for Part 5: **Advertising 4.x — architecture-ready / locally validated / feature-frozen / not pilot-ready**.

Meta Ads status for Part 5: **Meta Ads API — mock/future-ready / not active**.

Active Advertising data source: **manual entry / CSV import**.

## Part 5 rule

Finance 5.x must treat Advertising data as a **conditional manual/CSV source** until runtime/staging QA is completed and the known blockers registry is resolved.

Part 5 must not assume:

- live Meta spend sync exists;
- automatic attribution exists;
- token-based Meta connection exists;
- apply-sync exists;
- Advertising import has pilot-ready status;
- attributed revenue/profit has passed staging/browser QA.

## Safe for Finance MVP

| Data | Source | How Finance may use it | Guardrail |
|---|---|---|---|
| Order revenue | Sellora orders | Revenue totals, paid/valid order reporting, gross/net profit inputs | Use Sellora order status/payment rules; do not replace with Meta data |
| Order item cost | Sellora product/variant cost snapshots | COGS and gross profit inputs | Treat missing costs as incomplete/estimated, not fake zero profit |
| Manual ad spend | Manual Advertising metric entry | Period ad spend and ROAS/CPA/CPL context | Label source as manual |
| CSV ad spend | Advertising CSV import | Conditional ad spend source | Use with caution until B-ADV-003 passes |
| Manual campaign attribution | Leads/orders `campaign_id` where present | Optional attributed revenue/profit breakdowns | Use with caution until B-ADV-002 passes |

## Use with caution

- CSV-imported ad metrics until staging import QA passes.
- Attributed revenue/profit until browser attribution QA passes.
- Campaign insights as advisory only; they are not persisted backend GOOD/WATCH/PROBLEM/NO_DATA enums.
- ROAS based on manual/CSV ad spend only.

## Not ready for Part 5 dependencies

- Live Meta spend sync.
- Automatic attribution.
- Token-based Meta connection.
- Conversions API.
- Apply-sync.
- Meta sync DB writes.
- Production sync jobs.

## Future Finance formula dependencies

Documented for Part 5 planning only; no new Finance implementation is added in Sprint 4.14.

```text
Revenue = sum of paid/valid order totals
COGS = sum of product cost from order items
Gross profit = revenue - COGS
Ad spend = manual/CSV advertising spend for selected period
Net profit = revenue - COGS - ad spend - shipping costs - discounts - refunds - other expenses
Profit margin = net profit / revenue
ROAS = attributed revenue / ad spend
```

ROAS and ad spend can be included in Part 5 only as manual/CSV-based advertising data until Meta sync becomes active.

## Required Part 5 copy/UX guardrails

- Show Advertising source as manual/CSV where used in finance views.
- Explain when ad spend is missing, imported, or manually entered.
- Do not claim finance profit is complete if shipping, discounts, refunds, or other expenses are missing.
- Do not claim Meta Ads is connected or active.
- Do not mark Advertising or Advertising import as pilot-ready.

## Handoff recommendation

Part 5 can start with Sellora-side revenue, COGS, gross profit, and manual/CSV ad spend as conditional inputs. It must keep Advertising blockers visible and avoid any dependency on live Meta OAuth/API/token storage/apply-sync.

## Epic Sprint 5A implementation note

Finance 5A begins the Part 5 implementation with a read-only finance summary and `/finance` dashboard MVP. Finance uses Advertising data only as conditional manual/CSV source until Advertising runtime/staging blockers are resolved.

Meta Ads API is not active.

Sellora Finance MVP is operational profit analytics, not full accounting software. The first dashboard intentionally focuses on owner-facing clarity and data quality warnings instead of bank import, tax accounting, payment gateway reconciliation, or full бухгалтерія.
