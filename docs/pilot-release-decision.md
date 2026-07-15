# Pilot release decision

## Current decision

GREEN — GO FOR CONTROLLED GUIDED PILOT ✅

Controlled guided pilot is approved for staging-backed, closely monitored onboarding with synthetic or pilot-approved data. Unrestricted public production launch is not approved.

## Boundary

Allowed:
- guided OWNER/MANAGER/ANALYST pilot walkthroughs;
- synthetic QA workspaces;
- clearly labeled demo workspace data;
- controlled first-run validation and feedback collection.

Not allowed:
- public self-service signup;
- billing/subscriptions;
- live Meta/Instagram writes;
- real Nova Poshta TTN creation without explicit approval;
- production-data import without separate import hardening.

## Sprint 8B update

Sprint 8B keeps the controlled guided pilot GREEN by improving first-run guidance and adding a separate demo workspace path. The demo flow must remain synthetic and isolated from real workspaces.

## Next release path

Proceed to Sprint 8C — Import Center Pilot Hardening after Sprint 8B closure evidence is reviewed.

## Sprint 8C import decision update

Sprint 8C — APPROVED ✅. Import Center controlled pilot remains GREEN ✅ after template, dry-run, duplicate-policy, rollback and workspace-isolation hardening evidence. Controlled guided pilot remains GREEN ✅.

Public self-service production launch remains NOT APPROVED.

## Sprint 8D operations decision update

Sprint 8D — APPROVED ✅. Orders / Inventory / Local Shipments remain GREEN ✅ for controlled guided pilot use.

Public production launch remains NOT APPROVED.

## Sprint 8E Nova Poshta decision update

Orders / Inventory / Local Shipments — GREEN ✅. Controlled guided pilot remains GREEN ✅. Nova Poshta real TTN flow remains BLOCKED ⚠️ until approved staging secrets, `STAGING_NOVA_POSHTA_ALLOW_WRITES=true`, controlled TTN creation, status sync, cleanup, and browser/mobile evidence are collected. Public production launch remains NOT APPROVED.
