# Integration release control — 2026-10-20

Status: implementation/review in progress; this document does not record deployment or live activation.

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
