# Sellora 2.0 — scope amendment to Meta/Instagram specification

Date: 2026-10-20. The historical attached specification **version 1.0** was for configuration of Meta Business Suite/Instagram/Lead Ads only and explicitly excluded code, a CRM or SaaS. **This new scope is an amendment authorized by the owner**; it does not rewrite history.

## Product outcome

Meta Ads or organic Instagram → official Instagram Direct webhook → conversation → verified customer identity and products → confirmed order and stock → Nova Poshta shipment preview and explicit creation → tracking number → customer notification only on operator approval → attributed revenue/spend and profitability.

### Explicit requirements

- Read-only, bounded, idempotent history sync; no Instagram scraping outside Meta APIs.
- First-class conversations, customers, variants, orders, shipment operations and campaign IDs linked by stable evidence, not AI guesses.
- User verifies extracted order fields and shipping details before irreversible actions.
- Strict confirmation for external API writes; offer retry-safe operations and manual reconciliation.
- The dashboard must distinguish 0/unknown attribution and genuine read-only Meta Ads insight sync; expose date and attribution model.
- KPIs: spend, messages, qualified leads, orders, revenue, cost, shipping, net profit, CPA, ROAS.
- Protect personal data: session rotation, scoped roles, secret encryption, backup/restore, strict CSP rollout, safe logging, retention.
- Mobile-first Direct → customer/order/TTN flow, no duplicated actions. Desktop provides multi-pane list, inbox and analytics.

## Acceptance matrix

| Phase | Evidence to accept | Current state |
|---|---|---|
| Instagram OAuth | Live connected professional account, permissions and webhook verified | Connected; Meta dashboard approval not independently verified |
| Historical Direct | Repeatable deep-scan within Meta API limitations, no duplicates | Partial/needs canary |
| New sales | Synthetic E2E and real supervised test | Unit/integration subset passes; real E2E pending |
| Carrier | Preview, unique execute idempotency, reconcile, no duplicate TTN | Code tests; provider write not performed |
| Meta Ads | Ad account authorized read-only, real external IDs and spend | **Blocked: not connected** |
| Disaster recovery | Restore encrypted backup and offsite copy | Local restore passed; offsite missing |
| Security / UX | Sessions, CSP, PII-safe logs, mobile/desktop real QA | Sessions on staging; further hardening pending |

## No-go rules

No Meta write-mode, Instagram auto-send, real TTN or purchase conversion test without fresh approval; no source-of-truth claims based solely on local campaign IDs.

Full formatted owner-facing specification is separately delivered as `Sellora_TZ_v2_2026-10-20.docx`.
