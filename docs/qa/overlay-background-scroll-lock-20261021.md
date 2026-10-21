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
- html/body overflow locked directly via inline styles. The full-screen
  portal backdrop captures the pointer. Do not apply additional
  CSS-important overflow rules or disable nested app scroll containers:
  Chrome's wheel handling for React-portal children then stops working.
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

## Chrome regression finding

The shared dialog wrapper had overscroll-behavior: contain even though it is
not the scrolling pane. Chrome swallowed the wheel event over its
overflow-y-auto child. After removing that wrapper-level declaration in
Chrome, both 1440px and 390px passed: the nested drawer scroll advanced by
420px, background app scroll remained unchanged at 190px, and original lock
state and scroll position were restored after closing. The child retains
overscroll-contain via Tailwind.

## Final Chrome investigation — wrapper overflow

Chrome's wheel events could reach the scrollable dialog inner DIV without
moving it when its flex parent was overflow: hidden. Removing only wrapper
overscroll behavior was insufficient on the subsequent exact deployment.
Changing the wrapper to overflow: clip preserved visual clipping and removed
the synthetic scroll-container boundary. Direct Chrome test with this single
CSS override passed both 1440×900 and 390×844: +420px internal scroll,
unchanged 190px background scroll, original page position restored after close,
modal lock present and no real API mutations. Make this permanent on the
shared Drawer, Modal, BottomSheet and independent FeedbackDialog wrappers.
Verification of final deployed source must be repeated with NO test overrides.
