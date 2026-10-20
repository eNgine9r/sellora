# Integration release control — 2026-10-20

Status: final code review approved; final package, exact-head CI and controlled deployment gates remain pending. This frozen pre-release document does not record deployment or live activation; the PR release record and private runtime manifest carry rollout results.

## Scope

Nova Poshta owner onboarding uses the official cabinet key flow, named sender/contact/city/warehouse selection and explicit independent shipment-write permission. Meta Ads adds dedicated OAuth, explicit granted-account selection and owner-triggered read-only daily sync. Existing manual/CSV advertising data, CRM attribution and Instagram behavior must survive.

## Retained runtime baseline

- Backend source: 16f1946ac1b6b858c49ded8bb9a5224d0da0d807.
- Backend image: sha256:d7ba17d200b7e079ccecd970a24dff20497b55ce126c3bc1d2e425c8458c550f, ARM64.
- Frontend source: debd301567b57c18ed2e16ce8321f94d4c089d14.
- Frontend deployment: dpl_CZTKhf2HKNaddidwCUFAQnht8mxw at the existing sellora-web-staging.vercel.app alias.
- Schema: 202610200038; one Raspberry Instagram worker; outbound sending/auto-send disabled.
- Preserve the private effective environment, encryption/signing keys, deployment selectors, storage volume and original image. Do not include secrets in a release record.

## Release gates

1. Independent task reviews and final branch review close all material findings. Full exact-head CI, disposable PostgreSQL migration/ACL/concurrency tests and production-build synthetic desktop/mobile integration and Direct browser gates pass.
2. Migration039 extends038. Preflight external identity uniqueness and Supabase private-state grants. Fresh migration tests simulate inherited PUBLIC/anon/authenticated defaults. No production downgrade, stamping or data backfill.
3. Build the candidate from the exact audited backend dependency image. Verify architecture, release marker, source identity and startup with synthetic credentials on an internal test network.
4. Produce a distinct rollback compatibility package before migration. Original16f startup requires packaged038 and cannot restart on039. Add only the reviewed039 migration to exact16f; retain byte-identical old app/scripts and RELEASE_REVISION. Verify those bytes, exact-head startup and protected read/Direct/session behavior on039. Never relax the schema guard to accept unknown heads.
5. Immediately before production migration, create an encrypted backup and confirm archive integrity and an isolated restore. Record non-secret table counts, schema and credential equality checks privately. Keep provider/worker/send features disabled on restored test instances.
6. Run only the reviewed additive039 upgrade. Recreate only the Sellora backend using retained environment/storage. Update persistent image selector and watchdog expected-image guard deliberately. Verify one worker, health/readiness, cookie-session protections, row-count preservation and unchanged Instagram credentials.
7. Build the exact reviewed frontend revision with the Raspberry upstream and cookie-session mode. Use the configured staging preview deployment and existing alias; do not alias automatic builds lacking the upstream. Keep the previous deployment available.
8. Verify public routing/auth canaries and published-bundle synthetic scenarios. No real customer message, order, TTN or provider campaign mutation is a canary.

## Rollback

After039, restore the rehearsed compatibility package, retained effective environment and storage. Keep039. Restore the previous frontend alias. Update selectors/watchdog consistently and verify health/readiness, one worker and authentication. Do not restore an old036-only image, run database downgrade/stamp, delete tokens, or remove storage volumes. The unmodified16f image remains evidence but is not a valid post039 startup package.

## Activation remains separate

Deployment may leave Ads features fail-closed. Live Meta requires dedicated Ads app configuration, suitable access/approval, consent and an owner-selected account. Working Instagram callback variables and credentials must not be reused or changed. Ingress callback-query logging suppression is an activation gate. The frontend must remove callback secrets immediately and apply referrer/cache privacy.

Nova Poshta requires an owner-provided official cabinet key and valid sender setup. Verification does not enable TTN writes. A real shipment/payment/profit pilot needs a separately controlled recipient/order and explicit no-customer-send boundaries.

The first Ads integration supports manual sync only; it has no scheduled sync or automatic long-lived token exchange. Imported delivery/date fields are provider-controlled; CRM revenue/profit and local reach remain editable. Reach is not imported or represented as Meta unique reach. Currency mismatch blocks import; changing an existing workspace currency is not an integration workaround.

## Completed pre-release evidence

These checks concern synthetic disposable environments, not production activation:

- Reviewed backend implementation/fixes: 7cb428023c8fdef9ff1eece2d6954699b2824cbd; independent scoped review passed all three findings.
- CI39488127031 at cb67b0e: all seven jobs passed. This precedes the new Meta frontend; a final-head CI run is still required.
- Candidate image: sha256:040401aa5760c97410b3cca6c3471ba4ca5ecc75885fa3d948d76e7516ec0cc5; ARM64, UID10001. All302 packaged source/config/release files exactly match archived7cb source, with no extra or missing files. Tests used the packaged application, not a source override: 653 passed/37 explicitly skipped in the no-network suite; 61 PostgreSQL/transport/privacy tests passed after fresh packaged migrations.
- Rollback package: sellora-backend:rollback-16f1946-schema039-7cb4280, sha256:c970e7fb5e390490d9577440ae77ae587cfe0d7296c7cae7d2a751cf03b223a8. Byte comparison verified 295 old source/config/release files unchanged; only039 migration added. Thirteen actual-old-code Direct/session PostgreSQL tests passed.
- Disposable039 candidate → compatibility rollback → candidate startup rehearsal passed: health/readiness200, anonymous protected requests401, worker disabled, no schema downgrade. All test services were on an internal Docker network.

- Encrypted local snapshot from20:14UTC was restored directly into internal tmpfs PostgreSQL, with no plaintext archive persisted. Candidate migration038→039 added the state table; row digests/counts for all49 unchanged existing tables matched exactly. The existing connection-table row count was preserved.
- Application smoke on that restored clone used a newly seeded synthetic user/workspace: session-bound authenticated CRM/Direct reads succeeded, Ads status remained fail-closed, another workspace was denied403 and session revocation returned401. This does not establish real provider consent or independent off-host key recovery. A fresh encrypted backup is still required immediately before the eventual production migration.

## Integrated concurrency blocker — resolved in code review

A bounded PostgreSQL17 probe through the actual metric-update service and workspace-lock repository reproduced SQLSTATE40P01 when a CRM metric edit overlaps the Ads persistence lock path. Workspace FOR UPDATE conflicts with the audit foreign-key KEY SHARE while each transaction holds the other required row lock. All probe writes were rolled back on an isolated restored clone; production was unchanged. This is a new integration release blocker, not evidence of the historical Issue266 trigger.

The packaged7cb candidate above must not be deployed unchanged. Final review/fix must retain cross-process serialization, connection-generation revalidation, uniqueness and provider-field ownership while adding a deterministic real-PostgreSQL concurrent-edit/sync regression. A new backend package and exact-head CI are required after the fix.

Frontend implementation de528f7 passed all seven CI39493365697 jobs, including the new NP/Ads and existing Direct browser gates. Independent review found a stale OAuth callback deleting a newer pending attempt; d83db71 fixes that and the Ukrainian metric-source error copy. Scoped component, production callback and real StrictMode callback checks passed; independent re-review and final-head CI remain gates. These tests use intercepted synthetic APIs, not real provider consent.

## Final code review gate

Fix d1bab4ac8845ba1d39d9887250650df88ef36fcf changes the Ads workspace mutex to PostgreSQL FOR NO KEY UPDATE, retaining exclusive Ads serialization while permitting audit FK KEY SHARE. The actual emitted statement and a blocked second mutex session were tested. Deterministic actual-service CRM update/delete versus full sync failed with40P01 before the fix and passed afterward. Local CRM values, provider delivery, one campaign/day identity, audit persistence and durable delete conflicts are asserted. Four real manual/CSV insertion-overlap cases preserve inserted data and reject conflicting sync. Migration039 is unchanged.

The final scoped review approved I1 with no new fix breakage. Focused PostgreSQL/security/provider/privacy/inventory tests:83 passed. Full no-network backend:653 passed/44 skipped; seven added PostgreSQL cases account for the extra skips and pass in the PostgreSQL gate. These source-mounted tests do not replace the final packaged-image and exact-head CI gates.

Global normalized campaign-name serialization remains a pre-existing boundary: a newly created independent manual/CSV campaign can commit after the sync name snapshot; neither old nor new mutex guarantees predicate uniqueness. Existing data is not overwritten and subsequent sync detects the overlap. Historical static/document-marker harness debt is deferred; current behavior-based CI remains required.

The temporary per-task reports are removed from the final tree after its committed history and private review archive are retained. No product code is changed by this documentation cleanup.
