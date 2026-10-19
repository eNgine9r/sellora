# Sellora — bounded modernization context
2026-10-19. Source at a1a5d5a. Audit uses source tracing, not a claim of live provider operation.

## Records
- [Direct / orders / delivery](order-flow.md)
- [Desktop and mobile interface](ui.md)
- [Advertising and attribution](ads.md)
- Bounded function records in functions/.

## Cross-module rules
All business operations are workspace-scoped and server RBAC must remain authoritative. Existing fulfillment wizard and customer extraction are reused. No database/schema migration is required for this package. Historical reports and import sources retain their meanings.

## Confirmed friction
Direct search/filter controls do not change results; mobile hides Direct and stacks inbox above conversation. Reply draft is shared across selected customers. Generic order create and existing-shipment links fail to open the intended view. Wizard submits zero item costs. Advertising reports declared/imported metric sales rather than linked CRM orders; Instagram referral evidence and live Meta Ads transport are not currently wired end-to-end.

## Open questions and boundaries
No actual incoming Instagram event, purchase, TTN or customer send is created by this audit. Meta callback/worker cutover and real attachment reads remain separately unverified. Catalog cost defaults and product mention matching require later deliberate work; there is no catalog cost field to reuse. Live Meta connector activation requires provider registration and evidence, not synthetic previews. See records for exact evidence/assumptions.

## Implementation
[Bounded implementation plan](../docs/plans/2026-10-19-direct-sales-modernization.md): Direct workspace, order-cost/TTN handoff, source-separated CRM campaign sales, behavioral synthetic browser QA and read-only public canary.
