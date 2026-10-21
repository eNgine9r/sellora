"use client";

// Shared by portal-based dialogs/sheets. Keep one lock even when overlays nest,
// and restore the exact pre-dialog state only after the final overlay closes.
let lockCount = 0;
let restoreLastLock: (() => void) | null = null;

export function acquireOverlayScrollLock(): () => void {
  if (typeof document === "undefined") return () => undefined;

  if (lockCount === 0) {
    const html = document.documentElement;
    const body = document.body;
    const previousRootAttribute = html.getAttribute("data-sellora-scroll-locked");
    const position = { x: window.scrollX, y: window.scrollY };
    const bodyStyle = {
      overflow: body.style.overflow,
      position: body.style.position,
      top: body.style.top,
      left: body.style.left,
      width: body.style.width,
      paddingRight: body.style.paddingRight,
      overscrollBehavior: body.style.overscrollBehavior,
    };
    const htmlStyle = {
      overflow: html.style.overflow,
      overscrollBehavior: html.style.overscrollBehavior,
    };

    // Desktop Chromium cannot wheel-scroll an internal dialog reliably when
    // body is position:fixed. Only iOS WebKit needs that fallback to stop
    // page rubber-banding; other browsers use overflow and a modal backdrop.
    const isIOSWebKit = /iPad|iPhone|iPod/.test(navigator.userAgent)
      || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    const scrollbarGap = Math.max(0, window.innerWidth - html.clientWidth);
    if (scrollbarGap > 0) {
      body.style.paddingRight = `calc(${getComputedStyle(body).paddingRight} + ${scrollbarGap}px)`;
    }
    html.setAttribute("data-sellora-scroll-locked", "true");
    html.style.overflow = "hidden";
    html.style.overscrollBehavior = "none";
    body.style.overflow = "hidden";
    body.style.overscrollBehavior = "none";
    if (isIOSWebKit) {
      body.style.position = "fixed";
      body.style.top = `-${position.y}px`;
      body.style.left = `-${position.x}px`;
      body.style.width = "100%";
    }

    // Do not set inert on the app shell: React portal event ancestry can
    // otherwise suppress wheel scrolling inside the actual modal content.
    // The portal backdrop intercepts input, and document root overflow is
    // locked by inline styles. Never add global CSS-important overflow rules:
    // these interfere with nested scrolling in React portal dialogs.

    restoreLastLock = () => {
      if (previousRootAttribute === null) html.removeAttribute("data-sellora-scroll-locked");
      else html.setAttribute("data-sellora-scroll-locked", previousRootAttribute);
      html.style.overflow = htmlStyle.overflow;
      html.style.overscrollBehavior = htmlStyle.overscrollBehavior;
      body.style.overflow = bodyStyle.overflow;
      body.style.overscrollBehavior = bodyStyle.overscrollBehavior;
      body.style.position = bodyStyle.position;
      body.style.top = bodyStyle.top;
      body.style.left = bodyStyle.left;
      body.style.width = bodyStyle.width;
      body.style.paddingRight = bodyStyle.paddingRight;
      window.scrollTo(position.x, position.y);
    };
  }

  lockCount += 1;
  let released = false;
  return () => {
    if (released) return;
    released = true;
    lockCount -= 1;
    if (lockCount === 0) {
      const restore = restoreLastLock;
      restoreLastLock = null;
      restore?.();
    }
  };
}
