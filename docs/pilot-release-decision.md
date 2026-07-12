# Pilot Release Decision — Sprint 8A / 8A.1

## Decision

**RED — NO-GO**

Sellora staging must not be opened to controlled pilot shops yet.

## Current 8A.1 reason

Sprint 8A.1 attempted to close the access/runtime/E2E gaps, but required evidence is still blocked:

- frontend staging URL remains unreachable from this container because the proxy returned `CONNECT tunnel failed, response 403`;
- backend staging `/health` remains unreachable for the same reason;
- OWNER, MANAGER and ANALYST credentials were not available through secure `STAGING_*` environment variables;
- dedicated QA workspace ID was not available;
- runtime database revision was not verified and Sprint 7F remains blocked;
- read-only smoke could not pass G0/G1;
- controlled-write E2E was attempted with `STAGING_ALLOW_CONTROLLED_WRITES=true` but stopped before writes;
- workspace switching, cross-workspace negative checks, browser/mobile QA and console/network review were not executed.

## What is allowed

- Continue local automated validation.
- Prepare staging QA accounts and a dedicated synthetic QA workspace.
- Rerun `scripts/staging_release_gate.py` from a network that can reach Vercel/Render.
- Keep internal demos limited to clearly marked local/static evidence until staging passes.

## What is not allowed

- Do not claim GREEN, YELLOW, or pilot-ready status.
- Do not provide unrestricted external pilot write access.
- Do not run production migrations to close this gate.
- Do not use real customer/order data for smoke testing.
- Do not create real Nova Poshta shipments or real Meta Ads writes.

## Next release path

1. Run from an environment that reaches Vercel and Render.
2. Provide secure synthetic OWNER/MANAGER/ANALYST credentials and `STAGING_TEST_WORKSPACE_ID` outside the repository.
3. Verify runtime Alembic revision safely without executing migrations.
4. Rerun read-only and controlled-write smoke.
5. Complete browser/mobile/console QA.
6. If G0–G11 pass with no Critical/Major issues, reassess release decision as YELLOW or GREEN according to the release rules.
