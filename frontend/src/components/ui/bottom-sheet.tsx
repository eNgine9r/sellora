"use client";

import { ReactNode, useEffect, useId, useRef } from "react";
import { X } from "lucide-react";
import { Portal } from "@/components/ui/portal";
import { IconButton } from "@/components/ui/primitives";

export function BottomSheet({ open, title, closeLabel, children, onClose }: { open: boolean; title: string; closeLabel: string; children: ReactNode; onClose: () => void }) {
  const titleId = useId();
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const panelRef = useRef<HTMLElement | null>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    previousFocusRef.current = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = Array.from(panelRef.current.querySelectorAll<HTMLElement>("button, a, input, select, textarea, [tabindex]:not([tabindex='-1'])")).filter((element) => !element.hasAttribute("disabled") && element.tabIndex !== -1);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKeyDown);
    const id = window.setTimeout(() => closeButtonRef.current?.focus(), 0);
    return () => {
      window.clearTimeout(id);
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
      previousFocusRef.current?.focus?.();
    };
  }, [onClose, open]);

  if (!open) return null;

  return (
    <Portal>
      <div className="fixed inset-0 z-[200] md:hidden" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <button className="absolute inset-0 h-full w-full cursor-default bg-[var(--overlay-background)] backdrop-blur-sm" type="button" aria-label={closeLabel} onClick={onClose} />
        <section ref={panelRef} className="sellora-dialog-panel absolute inset-x-0 bottom-0 z-[210] flex max-h-[94dvh] min-w-0 flex-col overflow-hidden rounded-t-[28px] border border-b-0 border-border-subtle bg-surface-1 shadow-[var(--shadow-overlay)]">
          <div className="flex items-center gap-3 border-b border-border-subtle bg-surface-1/95 px-4 pb-3 pt-[max(0.75rem,env(safe-area-inset-top))] backdrop-blur">
            <div className="min-w-0 flex-1">
              <div className="mb-2 h-1.5 w-12 rounded-full bg-surface-3" aria-hidden="true" />
              <h2 id={titleId} className="truncate text-base font-black text-text-primary">{title}</h2>
            </div>
            <IconButton ref={closeButtonRef} variant="ghost" type="button" onClick={onClose} aria-label={closeLabel}>
              <X className="h-4 w-4" />
            </IconButton>
          </div>
          <div data-bottom-sheet-content className="sellora-scrollbar min-h-0 min-w-0 flex-1 overflow-x-hidden overflow-y-auto overscroll-contain px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-4">
            {children}
          </div>
        </section>
      </div>
    </Portal>
  );
}
