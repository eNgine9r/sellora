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

Controlled guided pilot remains GREEN ✅. Import Center pilot hardening is implemented locally, but Sprint 8C final approval is blocked until synthetic staging imports, duplicate rerun, rollback, workspace isolation, and browser/mobile import QA are executed.

Public self-service production launch remains NOT APPROVED.
