# Sellora Backend Agent Instructions

These instructions extend the root `AGENTS.md` for all files under `backend/`.

Before editing backend code, read:

1. `../PROJECT_PROFILE.yaml`;
2. `../docs/AI_DEVELOPMENT_OPERATING_STANDARD.md`;
3. `../.project/CURRENT_STATE.md`;
4. `../.project/ACTIVE_SPRINT.json`;
5. the linked GitHub Issue.

## Work Package discipline

- Implement one scoped Issue at a time.
- Respect the Issue's permitted directories and out-of-scope section.
- Record a dependency reason before changing files outside the declared scope.
- Do not combine unrelated cleanup, migrations or API changes.
- Update repository state and checkpoint files before ending the Work Package.

## Backend quality gates

For changed behavior, run the smallest relevant tests first, then the applicable completion checks:

```powershell
./scripts/verify-project.ps1 -Component Backend
```

Additional mandatory review applies to:

- workspace scoping;
- authentication and RBAC;
- inventory and order transitions;
- money/profit calculations;
- external provider state;
- Alembic migrations;
- destructive or irreversible operations.

Never claim a migration, test or runtime check passed unless it was actually executed against the referenced state.

## Autonomous continuation

Normal code edits, local tests, feature-branch commits, documentation updates and PR preparation do not require repeated user confirmation.

If a task is blocked, record the blocker and allow the Sprint runner to continue with another independent Ready Work Package. Stop only for the hard blockers defined in the operating standard and project profile.
