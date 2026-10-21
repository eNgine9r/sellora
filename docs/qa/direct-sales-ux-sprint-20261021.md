# Sprint Direct Sales 2.0 — QA findings and scope

**Environment:** Sellora staging, Next.js frontend + Raspberry Pi FastAPI backend.
**Shop:** existing Your Jewelry workspace and real Instagram Business integration.
**Safety:** no customer messages, no live order/TTN writes, no bulk history import during QA.

| Severity | Page | Issue | Expected / fix | Resolution |
|---|---|---|---|---|
| P0 | Direct → Order wizard | The wizard could allow selecting an unrelated CRM customer after opening from a Direct conversation. An order might be created even if subsequent Direct linkage fails. | Lock the form to its linked customer and reject a foreign/missing conversation–customer pairing in the backend **before** idempotency operations, order, reservation or TTN. | Implemented; regression tests. |
| P0 | Direct | Merely opening an order-intent conversation could POST ensure-customer, creating CRM records as a side effect of browsing. | Only mutate CRM on explicit manager action; preserve webhook-specific inbound order-intent automation separately. | Implemented. |
| P1 | Direct | Customer actions and status hidden inside the scrolling message timeline, while intent appears in a second unrelated badge. | Place one compact customer/sales context card near the thread, with clear next action and optional details. | Implemented. |
| P1 | Direct | Multiple direct triggers for 100/500-conversation bulk history sync exposed in ordinary messaging workflow. | Move into advanced section, default to 5 × 10, require explicit modal confirmation before any sync. | Implemented. |
| P1 | Direct | Reply CTA appeared actionable even when the backend send gate was disabled. | Respect live integration send_enabled in UI; label policy clearly, preserve all backend send guards. | Implemented. |
| P2 | Direct mobile | Large Instagram profile and technical details consume vertical thread space. | Put profile detail in a collapsed native disclosure. | Implemented. |
| P2 | Direct inbox | Large volume of messages and mixed intents can still become difficult to prioritize. | Later: server-side pagination, CRM-stage filter, last-message preview and accessible shortcuts. | Not in this sprint. |
| P1 | Authorized visual QA | Owner's signed-in browser is not automatically available to the sandbox smoke runner. | Inspect direct, wizard and order dialog at mobile and desktop with authorized session; do not claim pass if not checked. | Pending authorized browser test. |

## Product rules

1. **Reading ≠ creating:** no CRM client, order, TTN, product reservation or Meta message is created by opening Direct.
2. **Order ownership:** source Direct conversation and order customer must match and be in the same workspace before any fulfillment writes.
3. **Manual confirmation:** product match suggestions remain reviewed by the manager; no implicit sales.
4. **No old-history contamination:** imported Instagram conversations are not counted as new sales merely because a manager opens them.
5. **Financial integrity:** delivered and COD paid remain distinct; no payment side effects in this sprint.
6. **No legacy Render:** maintain stacked Draft PR; deploy exact branch SHA to Raspberry/Vercel staging only.

## QA verification

- Backend targeted: direct-linked order ownership acceptance and rejection without any operations.
- Backend full regression and frontend typecheck/lint/Next production build.
- No-memcg isolated PostgreSQL and health smoke on exact ARM64 Docker image.
- Read-only live workspace aggregates before/after release, along with Meta flags.
- Chrome mobile anonymous login and authorization redirects; separately track authenticated UI as pending.
