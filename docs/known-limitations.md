# Sellora Known Limitations for Pilot Users

Sellora is approved for a controlled guided MVP pilot. The following limitations remain and must be communicated before pilot shops rely on the platform for daily operations.

## External integrations not fully active

- Instagram Direct API ingestion is not connected.
- Meta Ads live OAuth, token storage, automatic synchronization and Conversions API are not active.
- Manual entry and CSV remain the supported advertising data sources.
- Nova Poshta real TTN creation and production status behavior require a separate controlled validation with a shop-owned credential.
- Nova Poshta background status synchronization is not enabled.
- Printable/downloadable TTN documents are not implemented.

## Commercial and onboarding scope

- Billing and subscriptions are not implemented.
- Unrestricted public self-service onboarding is not approved.
- Email invitations and password reset remain incomplete or outside the currently approved pilot scope.
- Organization-level super-admin capabilities are not part of the MVP pilot.

## AI and automation scope

- AI Direct parsing is not implemented.
- Predictive analytics and advanced AI recommendations are not implemented.
- Advertising guidance is deterministic and based on manual/imported data, not live Meta recommendations.

## Data and import boundaries

- Reports depend on the completeness of operational, manual and imported data.
- Import dry-run should be used before executing imports.
- Real business files must be sanitized before QA or support sharing.
- Passwords, tokens, API keys, full authorization headers, private customer exports and private spreadsheets must not be placed in feedback, screenshots, logs or issue comments.
- Deep advertising CSV import behavior remains a dedicated follow-up beyond the Sprint 8A.1 route/browser smoke.

## Inventory follow-up

Issue #134 tracks an edge case where archiving a product variant may leave a visible zero-stock inventory row.

Current impact:

- stock can be returned to zero;
- order reservation and inventory calculations passed the controlled-write E2E;
- the issue affects cleanup/visibility semantics rather than the verified commerce flow;
- it does not block the controlled pilot, but should be resolved before broader rollout.

## Shipment limitations

- Shipment drafts are pilot-ready.
- Real Nova Poshta provider actions were intentionally not called during Sprint 8A.1.
- TTN creation does not automatically complete an order; shipment and order statuses remain separate.
- TTN cancellation is not fully production-validated.
- Pilot users should use the Nova Poshta cabinet for printing until document generation is implemented.

## PWA and mobile limitations

- Browser/mobile QA passed at 375 × 812, 390 × 844, 430 × 932 and 768 × 1024.
- PWA installation on real iOS and Android devices remains a separate device-level validation.
- Offline caching of private CRM, finance, customer, order, workspace or token data is intentionally not enabled.

## Security and audit limitations

- Role authentication and representative tenant-isolation checks passed.
- Workspace A/B stale-data checks passed in browser QA.
- Audit logging is not yet standardized for every critical mutation.
- Pilot access should remain controlled, with explicit workspace memberships and least-privilege roles.
- Synthetic credentials used for QA should be rotated or removed after the testing window.

## Staging and deployment operational notes

Sprint 8A.1 resolved a Render incident where the Docker image could not locate Alembic revision `202607130021`.

The backend image now verifies the expected Alembic revision during build and startup. Runtime and packaged head both matched `202607130021` in the approved deployment.

Future deployment rules:

1. deploy from the approved `main` branch;
2. keep Render root directory and Docker build context aligned;
3. fail the image build when the expected revision is absent;
4. verify `/health` before browser or controlled-write QA;
5. rerun the same Sprint 8A.1 gate after migration, auth, tenant-isolation or core-flow changes.

## Sprint 8A.1 closure status

The following former blockers are closed:

- staging frontend access;
- backend health access;
- synthetic OWNER/MANAGER/ANALYST credentials;
- dedicated QA workspace;
- runtime Alembic verification;
- read-only gate;
- controlled-write E2E;
- browser/mobile QA;
- console/network review;
- workspace switching and stale-data validation.

Final result:

```text
Sprint 8A.1: APPROVED
Release decision: GREEN
Pilot scope: controlled and guided
```

These limitations do not reverse the approval. They define the boundaries within which the controlled pilot may operate safely.