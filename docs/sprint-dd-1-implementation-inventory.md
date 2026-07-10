# Sprint DD.1 implementation inventory

Date: 2026-07-10

## Frontend architecture observed

- App router lives in `frontend/src/app` with a root provider stack in `layout.tsx`.
- Protected navigation is centralized in `frontend/src/components/app-shell.tsx`, with sidebar, topbar, mobile bottom navigation, and workspace onboarding handling.
- Shared cross-feature components live in `frontend/src/components`; feature-specific UI lives under `frontend/src/features/*/components`.
- Localization is handled through `frontend/src/i18n/provider.tsx` and JSON dictionaries in `frontend/src/i18n/messages`.
- Styling is Tailwind CSS with global CSS custom properties in `frontend/src/app/globals.css` and Tailwind token wiring in `frontend/tailwind.config.ts`.

## Existing shared UI surface

- App shell: `app-shell.tsx`, `app-sidebar.tsx`, `app-topbar.tsx`, `mobile-more-sheet.tsx`.
- Overlays/dialogs: `form-dialog.tsx`, `confirm-action-dialog.tsx`, `edit-record-dialog.tsx`, `feedback-dialog.tsx`, `ui/bottom-sheet.tsx`, `ui/portal.tsx`.
- Feedback states: `ui/states.tsx`.
- Controls: `pagination-controls.tsx`, `filter-controls.tsx`, `date-range-selector.tsx`, `language-switcher.tsx`, `theme-toggle.tsx`.

## Sprint DD.1 implementation choices

- Extend the current Tailwind/CSS-variable design-token approach instead of adding a new design system dependency.
- Add small shared primitives that can be adopted incrementally by existing pages without rewriting feature modules.
- Keep the protected App Shell behavior centralized and improve semantics/resilience rather than moving route logic.
- Keep Ukrainian as the default user-facing copy and avoid backend/API enum changes.
