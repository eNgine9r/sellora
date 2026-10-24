# AI Development Operating Standard

Version: 1.0  
Effective date: 2026-07-31

This document is the shared operating model for product planning, implementation, verification and continuity across ChatGPT, Codex, PowerShell and GitHub.

## 1. Core principle

The conversation is a working interface, not the permanent project memory.

The repository and GitHub are the source of truth:

- `PROJECT_PROFILE.yaml` — runtime and infrastructure constraints;
- `.project/CURRENT_STATE.md` — verified current state and next action;
- `.project/ACTIVE_SPRINT.json` — ordered, machine-readable Sprint queue;
- `.project/BLOCKERS.md` — unresolved blockers and required decisions;
- GitHub Issues — complete Work Packages;
- Pull Requests — reviewed implementation units;
- architecture decisions and runbooks — durable technical knowledge.

A new chat or Codex session must be able to resume work from these sources without reconstructing the whole conversation history.

## 2. Roles

### Product Owner — user

Responsible for:

- product goal and business priority;
- real-world workflow and usability feedback;
- acceptance of major product compromises;
- access to hardware, test data and external accounts;
- approval of destructive or production-critical operations.

The Product Owner is not required to write technical specifications, select libraries, design the database or manage test commands.

### ChatGPT — Team Lead / Senior / Architect

Responsible for:

- discovery and requirements synthesis;
- technology and integration discovery before implementation;
- architecture, security boundaries and roadmap;
- conversion of natural-language requests into GitHub Work Packages;
- scope, dependencies, acceptance criteria and Definition of Done;
- sequencing vertical product slices;
- review of implementation, CI and runtime evidence;
- keeping repository state files synchronized;
- warning about future migration cost, paid dependencies and offline constraints.

### Codex — Implementation Engineer

Responsible for:

- one scoped Work Package at a time;
- repository inspection within the permitted scope;
- implementation, targeted tests and local verification;
- honest reporting of commands actually executed;
- maintaining clean diffs and avoiding unrelated refactors;
- recording a checkpoint before the session ends.

Codex must not independently redefine product scope, architecture, data ownership or security boundaries.

### PowerShell Sprint Runner — execution coordinator

Responsible for:

- reading `.project/ACTIVE_SPRINT.json`;
- selecting the next unblocked Ready Work Package;
- creating a scoped Codex prompt;
- recording logs and checkpoints;
- continuing after soft blockers;
- stopping on hard blockers or exhausted usage limits.

### GitHub — durable control plane

Responsible for:

- Issues, branches, Pull Requests and review history;
- CI status and release evidence;
- source-controlled documentation;
- recovery after chat, client or agent interruption.

## 3. Project profiles

Every project must declare exactly one primary profile in `PROJECT_PROFILE.yaml`:

- `CLOUD_SAAS` — internet-facing hosted product;
- `LOCAL_DESKTOP` — application on one workstation;
- `LOCAL_LAN` — local server with LAN clients;
- `HYBRID` — core works locally, optional online features are isolated.

The profile must explicitly state:

- whether internet is allowed during development;
- whether internet is required at runtime;
- whether paid runtime services are allowed;
- supported operating systems;
- deployment and update method;
- data location and backup requirements;
- required external integrations.

No mandatory runtime dependency may be introduced in conflict with the profile.

## 4. Mandatory project gates

No new project proceeds directly from idea to code.

### Gate 0 — Product Discovery

Produce or update:

- problem statement;
- users and roles;
- core workflows;
- MVP scope and explicit out-of-scope;
- success criteria and constraints.

### Gate 1 — Technology and Integration Discovery

Evaluate before implementation:

- authentication;
- database and file storage;
- background work and scheduling;
- monitoring and auditability;
- analytics;
- UI system;
- external APIs;
- realtime communication;
- AI requirements;
- backup, restore and update strategy;
- local/free alternatives to paid services.

Each option is recorded as `USE_NOW`, `PLAN_FOR_LATER`, `NOT_NEEDED` or `REJECTED` with rationale.

### Gate 2 — Architecture

Define:

- system boundaries and components;
- data model and ownership;
- API and event contracts;
- roles and permissions;
- security boundaries;
- deployment environments;
- failure, recovery and rollback paths.

### Gate 3 — Roadmap

Use the hierarchy:

`Vision → Milestone → Epic → Sprint → Issue → Pull Request`

Roadmaps are organized by vertical product slices, not by disconnected pages.

### Gate 4 — Implementation Readiness

A Work Package is `Ready` only when it has:

- problem and business outcome;
- current and expected behavior;
- scope and out-of-scope;
- dependencies;
- acceptance criteria;
- technical constraints;
- permitted directories;
- verification commands;
- Definition of Done.

### Gate 5 — Verification and Release

Implementation is not Done until required evidence exists for code, runtime and user flow.

## 5. Work-in-progress rules

- One primary vertical feature may be active at a time.
- One additional critical bugfix may interrupt it.
- New ideas go to Backlog unless classified as a Critical Bug or approved Architecture Change.
- One Issue maps to one branch and one focused Pull Request.
- Unrelated cleanup is not bundled into a feature PR.
- Architecture changes require a recorded decision before implementation.

## 6. Autonomous Sprint Mode

A Sprint is represented by `.project/ACTIVE_SPRINT.json`.

The runner processes Ready tasks whose dependencies are Done or Review-ready.

After each Work Package:

1. run targeted verification;
2. record the result and changed scope;
3. update `.project/CURRENT_STATE.md`;
4. write `.project/LAST_CHECKPOINT.json`;
5. create or update the focused Pull Request when publishing is enabled;
6. continue to the next independent Ready task.

The system is a chain of small resumable sessions, not one unbounded agent conversation.

## 7. Blocker policy

### Soft blocker

Examples:

- one optional integration credential is missing;
- a noncritical external service is unavailable;
- one task has a failing dependency but other tasks are independent;
- a documentation question does not affect current implementation.

Action:

- record it in `.project/BLOCKERS.md`;
- mark the affected task `blocked`;
- continue with the next independent Ready task.

### Hard blocker

Stop and request explicit user action only for:

- destructive production migration or data deletion;
- production DNS, billing or account ownership changes;
- secret exposure or missing mandatory credentials;
- hardware write operations with safety risk;
- two materially different product choices without an accepted decision;
- inability to protect stable data or runtime;
- exhausted Codex/service usage limits;
- no remaining independent Ready work.

Normal file edits, local tests, feature branches, commits, PR creation, CI inspection and documentation updates are not hard blockers.

## 8. Verification ladder

Use the smallest useful check first.

### During implementation

- targeted test;
- formatter or static check for touched files;
- contract/schema validation when relevant.

### At Work Package completion

- module tests;
- lint;
- typecheck or compile check;
- migration consistency when relevant.

### Before Pull Request approval

- integration tests;
- production build;
- security and isolation checks;
- browser or API verification;
- updated documentation and checkpoint.

### Before merge/release

- required CI status checks;
- staging verification for cloud projects;
- offline readiness verification for local projects;
- rollback or recovery evidence for high-risk changes.

Never claim a check passed unless it was actually executed against the referenced commit or environment.

## 9. Offline readiness for local projects

For `LOCAL_DESKTOP`, `LOCAL_LAN` and offline portions of `HYBRID`, verify:

- installation from an offline package;
- startup with internet physically unavailable;
- local authentication and authorization;
- database and local storage operation;
- hardware and device communication;
- absence of mandatory CDN, cloud font, telemetry or external API calls;
- local logs and diagnostics;
- backup creation and restore;
- offline update and rollback;
- safe behavior after power loss or service restart.

External AI or cloud functions must be optional, isolated and visibly unavailable offline unless a local model is provided.

## 10. Codex efficiency rules

- One Codex session handles one Work Package.
- Use exact permitted directories and acceptance criteria.
- Read project state files instead of replaying chat history.
- Run targeted checks before the full suite.
- Use resume/checkpoint after interruption instead of re-analyzing the entire repository.
- Do not ask Codex to “review and fix everything”.
- Use stronger reasoning only for architecture, security, migrations and difficult root-cause analysis.
- Do not attempt to bypass usage limits.

## 11. Git and GitHub rules

- No direct feature work on `main`.
- No force push to protected branches.
- Branch names should identify the issue or Work Package.
- Pull Requests contain one logical change and link the Issue.
- Required checks must be green before merge.
- Review conversations must be resolved.
- Production-critical operations require explicit evidence and approval.
- Secrets, tokens and personal data never enter commits, logs, screenshots or PR descriptions.

## 12. State continuity protocol

At the start of every ChatGPT or Codex session:

1. read `PROJECT_PROFILE.yaml`;
2. read this operating standard;
3. read the applicable `AGENTS.md` files;
4. read `.project/CURRENT_STATE.md`;
5. read `.project/ACTIVE_SPRINT.json`;
6. inspect linked Issues, open PRs and the current branch;
7. reconcile documentation with actual code before claiming current status.

At the end of every Work Package:

- update task status;
- record checks and evidence;
- update current state and next action;
- record blockers;
- leave the repository recoverable from the last commit/checkpoint.

## 13. Standard status report

Every implementation result must report:

```text
Outcome
Scope completed
Files changed
Checks actually run
Runtime evidence
Open blockers
Risks
Next Ready Work Package
```

## 14. Priority of instructions

When instructions conflict, use this order:

1. current explicit user requirement;
2. safety, legal and data-protection constraints;
3. project `AGENTS.md` and accepted architecture decisions;
4. `PROJECT_PROFILE.yaml` runtime constraints;
5. this operating standard;
6. active Issue and Sprint queue;
7. existing code conventions;
8. general best practices.

Project-specific security and domain rules remain authoritative over generic workflow guidance.