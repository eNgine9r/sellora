# Pilot Release Decision — Sprint 8A

## Decision

**RED — NO-GO**

Sellora staging must not be opened to controlled pilot shops yet.

## Reason

Sprint 8A could not collect the required staging evidence:

- frontend staging URL was unreachable from this container because the proxy returned `CONNECT tunnel failed, response 403`;
- backend staging `/health` was unreachable for the same reason;
- OWNER, MANAGER and ANALYST credentials were not available through secure `STAGING_*` environment variables;
- runtime database revision was not verified and Sprint 7F remains blocked;
- the synthetic Lead → Customer → Product/Variant → Inventory → Order flow was not executed;
- mobile/browser/console QA evidence was not collected.

## What is allowed

- Continue local automated validation.
- Prepare staging QA accounts and a dedicated synthetic QA workspace.
- Rerun `scripts/staging_release_gate.py` from a network that can reach Vercel/Render.
- Keep read-only internal demos limited to already-verified local behavior and clearly label staging gate as blocked.

## What is not allowed

- Do not claim GREEN or pilot-ready status.
- Do not provide unrestricted external pilot write access.
- Do not run production migrations to close this gate.
- Do not use real customer/order data for smoke testing.
- Do not create real Nova Poshta shipments or real Meta Ads writes.

## Next release path

1. Unblock Sprint 7F runtime PostgreSQL migration QA or independently verify staging database compatibility safely.
2. Provide secure synthetic OWNER/MANAGER/ANALYST staging credentials and a dedicated QA workspace.
3. Rerun Sprint 8A staging release gate from an allowed network.
4. If G0–G11 pass with no Critical/Major issues, reassess release decision as YELLOW or GREEN according to the release rules.
