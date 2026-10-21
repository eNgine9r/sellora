# Mobile hamburger navigation — background scroll leak

**Severity:** P1
**Affected screen:** Authenticated Sellora mobile AppShell; same lock pattern on public mobile header.
**Issue:** The hamburger menu used a body-only overflow class. The AppShell container has overflow-x-hidden, which can create an independently scrolling vertical surface on mobile. The user could scroll content behind the open navigation overlay.

## Expected
- Opening hamburger fixes the underlying page at the current position.
- The menu's own long navigation list is scrollable without moving background content.
- Dismissing via overlay, choosing a route or pressing Escape restores original scroll position and styles.
- The menu lock cooperates with any nested modal/sheet, including on mobile Safari; no double-release.
- No data changes, API writes, Meta sends, Nova Poshta, accounts or orders during QA.

## Fix
- Use existing shared reference-counted acquireOverlayScrollLock() utility instead of body overflow class; release on close/unmount.
- Render the mobile menu using a React portal directly into document.body, outside AppShell's independent overflow-x-hidden scroll container. Keep the AppShell layout and its scroll position unchanged.
- Keep the sidebar nav as an independently scrollable overscroll-contained region; outer panel uses overflow-clip rather than becoming a scroll container.
- Escape closes the menu; public mobile header uses the same centralized lock.
- Frontend only; no Raspberry backend changes.

## QA
- TypeScript, ESLint, Next.js Vercel production build.
- Google Chrome synthetic-auth tests at 390px and 320px; test background wheel/touch attempts while menu open, menu internal wheel scroll, Escape/backdrop close and restoration. Network writes blocked.
- Public mobile header with real unauthed landing page: backdrop close, viewport restored.
- Real iOS Safari device QA remains separate from Chromium emulation.


## Chrome diagnosis during pre-release validation

The initial implementation temporarily changed AppShell overflow to clip when opening the menu. Chrome revealed that this reset a scrolled page position (115px -> 0px) even though later wheels no longer moved the background. This is unacceptable.
The final version instead portals the fixed menu to document.body and uses the existing shared root scroll lock with no AppShell overflow changes. The final deployed Chrome regression must verify the original scroll offset is unchanged both while open and after close, and internal menu scrolling remains functional.


## Mobile Chrome scroll-offset preservation

Even with the menu portaled outside AppShell, Mobile Chrome may reset the
document's numeric scrollY when root overflow becomes hidden. To preserve
the *visual* background position, mobile hamburger menus request the shared
scroll utility's forceFixedBody option. It fixes the body at the negative
pre-open scroll offset and restores original window.scrollY on final release.
Other overlays keep their prior behavior; this branch changes only menu calls.
Chrome QA checks body.style.top against the pre-open scrollY, ensures it does
not move on backdrop wheel/touch gestures, and verifies the restored scrollY.
