# QA — Prevent background scrolling behind Sellora dialogs

**Severity:** P1 (user-visible UX inconsistency)
**Surface:** Shared Modal, Drawer, ConfirmationDialog, BottomSheet and FeedbackDialog across desktop and mobile.

## Observed

Opening a dialog previously locked only document.body overflow.
Sellora desktop app has a separate nested scrolling main content pane, so
wheel scrolling could still move the background. Other dialogs used
independent overflow effects that could conflict if dialogs overlapped.

## Expected

1. On open, background viewport and nested app content do not scroll.
2. The modal or drawer still scrolls its own tall content normally.
3. Closing restores exactly the original page position.
4. Overlapping dialogs use reference-counted locks: closing one never
   re-enables scrolling while another remains.
5. On cleanup preserve prior inline styles, overflow attribute and focus.
6. Desktop Chromium must not use fixed body positioning (it interferes
   with overlay wheel scrolling). iOS Safari retains a fixed-body fallback.
7. No CRM, Meta, Nova Poshta or database mutations.

## Implementation

- One shared reference-counted lock utility for all portal-based dialogs,
  bottom sheets and the feedback dialog.
- html/body overflow locked and app's separately scrolling main pane
  locked by CSS while a dialog is open.
- Preserve scroll position and original styles.
- Do not inert the app root: Chrome also suppressed wheel scroll events
  in React portal content.

## QA

- Run frontend/scripts/test-overlay-scroll-lock.mjs for nested locks,
  idempotent cleanup, original style restoration and iOS fallback.
- TypeScript, ESLint and Next.js optimized build.
- Chrome 1440px and 390px, synthetic browser auth/API; test wheel behind
  drawer, internal drawer scroll, closing restoration and real confirmation
  modal with no network mutations.
- Production Vercel staging smoke on exact commit, no backend rollout.
