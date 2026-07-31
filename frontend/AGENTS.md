# Sellora Frontend Agent Instructions

These instructions extend the root `AGENTS.md` for all files under `frontend/`.

Before editing frontend code, read:

1. `../PROJECT_PROFILE.yaml`;
2. `../docs/AI_DEVELOPMENT_OPERATING_STANDARD.md`;
3. `../.project/CURRENT_STATE.md`;
4. `../.project/ACTIVE_SPRINT.json`;
5. the linked GitHub Issue.

## Work Package discipline

- Implement one scoped Issue at a time.
- Build a complete user flow, not an isolated screenshot or page fragment.
- Respect permitted directories and explicit out-of-scope boundaries.
- Reuse the current design system, localization and API client conventions.
- Do not introduce hidden mock/fallback data into live flows.
- Update current state and checkpoint files before ending the Work Package.

## Frontend completion states

Every touched flow must account for applicable:

- loading;
- empty;
- success;
- validation;
- authorization;
- offline/network error;
- provider/API error;
- mobile and desktop behavior.

Run targeted tests first, then the applicable completion checks:

```powershell
./scripts/verify-project.ps1 -Component Frontend
```

Browser and staging evidence is required before a user-facing change is approved.

## Autonomous continuation

Normal code edits, local tests, feature-branch commits, documentation updates and PR preparation do not require repeated user confirmation.

If one UI task is blocked, record it and continue only with another independent Ready Work Package. Stop for the hard blockers defined in the operating standard and project profile.
