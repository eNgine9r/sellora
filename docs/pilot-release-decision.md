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

Controlled guided pilot remains GREEN ✅. Orders, Inventory and local Shipment hardening are implemented locally, but Sprint 8D final approval is blocked until staging controlled-write scenarios, browser/mobile QA and synthetic cleanup are executed.

Public production launch remains NOT APPROVED.
