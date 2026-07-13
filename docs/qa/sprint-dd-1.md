# Sprint Dd.1 / Dd.1.1 QA Notes

## Runtime environment tested

- Local repository commit under test: `f831726` plus Sprint Dd.1.1 closure fixes on the current branch.
- Automated runtime used for validation: local Next.js production build via `npm run build` in `frontend/`.
- Staging deployment commit verification: not available from this container. No staging URL, authenticated test account, or deployment metadata environment variables were present, so the deployed staging build could not be confirmed.
- Authenticated browser QA: not executed. This environment does not provide a browser automation runtime or authenticated Sellora workspace credentials.

## Automated checks run

- `npm run typecheck` — passed.
- `npm run build` — passed.
- `npm run lint` — passed with warnings after migrating from deprecated interactive `next lint` to non-interactive `eslint .`.
- `node frontend/scripts/localization-regression.mjs` — passed.
- `node frontend/scripts/auth-api-boundary-regression.mjs` — passed.
- `node frontend/scripts/mobile-ux-pwa-mvp-regression.mjs` — passed.
- `git diff --check` — passed.

## Lint migration

Sprint Dd.1.1 replaced the deprecated interactive `next lint` script with `eslint .` and added `frontend/eslint.config.mjs` using the existing Next.js `core-web-vitals` and `typescript` presets. No broad formatting pass was run.

The migrated lint command exits successfully. Existing warnings remain for older unused variables, hook dependency warnings, and image optimization suggestions in areas outside the App Shell scope; they are not Dd.1 regressions.

## Viewport matrix

| Viewport | Browser/auth result | Notes |
| --- | --- | --- |
| 1280×800 | Pending | Requires authenticated browser session. |
| 1366×768 | Pending | Requires authenticated browser session. |
| 1440×900 | Pending | Requires authenticated browser session. |
| 1536×1024 | Pending | Requires authenticated browser session. |
| 1920×1080 | Pending | Requires authenticated browser session. |
| 1024×768 | Pending | Requires authenticated browser session. |
| 768×1024 | Pending | Requires authenticated browser session. |
| 430×932 | Pending | Requires authenticated browser session. |
| 390×844 | Pending | Requires authenticated browser session. |
| 375×812 | Pending | Requires authenticated browser session. |

## Authenticated flow checklist

| Flow | Result | Notes |
| --- | --- | --- |
| No horizontal body scroll | Pending browser QA | Static shell still uses `overflow-x-hidden` and `min-w-0`; runtime measurement pending. |
| Sidebar does not overlap content | Pending browser QA | Shell keeps 240px sidebar with matching `lg:pl-60`; runtime measurement pending. |
| Sidebar collapse and navigation | Pending browser QA | No route or permission logic changed; visual test pending. |
| Topbar controls visible and usable | Pending browser QA | Controls were retokenized; click/keyboard test pending. |
| Profile/workspace panel opens/closes | Pending browser QA | Existing component preserved; test pending. |
| Workspace switching cache safety | Pending browser QA | Query/auth logic unchanged; authenticated switch test pending. |
| Global Create CTA real action only | Pending browser QA | CTA still routes to `/orders`; no fake action added. |
| Language and theme controls | Pending browser QA | Existing controls preserved; test pending. |
| Logout/login/reload/session restore | Pending browser QA | Auth/session code unchanged; test pending. |
| Mobile drawer and bottom navigation | Pending browser QA | Existing mobile shell markers still pass script regression. |
| Dialog/sheet keyboard accessibility | Pending browser QA | Overlay foundation includes ESC close, focus trap, focus restore, and body scroll lock; real-browser test pending. |
| Ukrainian labels do not overflow controls | Pending browser QA | Requires visual viewport verification. |

## Defects found and fixes applied

- **Confirmed static defect:** Tailwind theme did not expose Dd.1 semantic status colors to classes with opacity modifiers such as `bg-danger/10` and `border-danger/25`. Fixed by extending `tailwind.config.ts` with semantic `canvas`, `sidebar`, `surface`, `text`, `success`, `warning`, `danger`, `info`, and `focus.ring` colors.
- **Confirmed lint blocker:** `npm run lint` used deprecated interactive `next lint`. Fixed by adding a flat ESLint config and changing the script to `eslint .`.
- **Confirmed lint errors:** Existing explicit `any` casts and a CommonJS Tailwind plugin import caused lint failures after migration. Fixed the two casts with narrower types and switched Tailwind plugin loading to an ESM import.
- **Confirmed App Shell warning:** Removed an unused `MoreHorizontal` import from `AppShell`.

## Current status

Sprint Dd.1 implementation is stable under typecheck, build, lint, localization regression, auth/API boundary regression, mobile UX/PWA regression, and whitespace checks.

Final browser-dependent acceptance remains pending because authenticated staging/local browser QA could not be executed in this environment.


## Manual browser verification closure

Sprint Dd.1 manual browser verification was completed before Sprint Dd.2 kickoff per product instruction. No Dd.1 implementation changes were required for this status update.

Final Sprint Dd.1 status: APPROVED.

## Sprint Dd.2.1 dual-theme note

Dd.2.1 added light-theme semantic token hardening for shared Dd.1 foundations without changing protected business logic, routes, RBAC, workspace isolation, or auth/session behavior.
