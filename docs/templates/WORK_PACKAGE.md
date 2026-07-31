# Work Package: <outcome-oriented title>

## Problem

Describe the verified current problem. Separate observed facts from assumptions.

## Business outcome

Describe what becomes possible or safer for the user when this Work Package is complete.

## Current behavior

- ...

## Expected behavior

- ...

## Scope

- ...

## Out of scope

- ...

## Dependencies

- Issue / decision / service / hardware dependency

## Permitted directories

```text
path/to/module
path/to/tests
```

Changes outside these paths require a documented dependency reason.

## Acceptance criteria

- [ ] ...
- [ ] ...

## Technical constraints

- Preserve existing architecture and public contracts unless explicitly approved.
- Do not add secrets, production data or hidden fallback behavior.
- Keep workspace isolation and backend RBAC intact.

## Verification commands

### Targeted

```text
<fast checks for the touched module>
```

### Completion

```text
<module tests, lint, typecheck, migration checks>
```

### Release evidence

```text
<CI, staging, browser/API evidence>
```

## Blocker policy

- Soft blockers are recorded and the runner continues with independent Ready work.
- Hard blockers require explicit user action before continuing.

## Definition of Done

- [ ] Acceptance criteria met.
- [ ] Tests added or updated where behavior changed.
- [ ] Required checks actually passed.
- [ ] Pull Request is focused and linked to this Issue.
- [ ] `.project/CURRENT_STATE.md` updated.
- [ ] `.project/LAST_CHECKPOINT.json` written.
- [ ] Risks and next Ready Work Package recorded.
