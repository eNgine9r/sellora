"use client";

import { ReactNode, useEffect, useRef } from "react";
import { X } from "lucide-react";
import { Portal } from "@/components/ui/portal";

export function BottomSheet({ open, title, closeLabel, children, onClose }: { open: boolean; title: string; closeLabel: string; children: ReactNode; onClose: () => void }) {
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab") return;
      const focusable = Array.from(document.querySelectorAll<HTMLElement>("[data-bottom-sheet-content] button, [data-bottom-sheet-content] a, [data-bottom-sheet-content] input, [data-bottom-sheet-content] select, [data-bottom-sheet-content] textarea, [data-bottom-sheet-content] [tabindex]:not([tabindex='-1'])")).filter((element) => !element.hasAttribute("disabled") && element.tabIndex !== -1);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    window.setTimeout(() => closeButtonRef.current?.focus(), 0);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [onClose, open]);

  if (!open) return null;

  return (
    <Portal>
      <div id="mobile-more-sheet" className="fixed inset-0 z-[200] md:hidden" role="dialog" aria-modal="true" aria-label={title}>
        <button className="absolute inset-0 h-full w-full cursor-default bg-slate-950/55 backdrop-blur-sm" type="button" aria-label={closeLabel} onClick={onClose} />
        <section className="absolute inset-x-0 bottom-0 z-[210] max-h-[min(88dvh,760px)] overflow-hidden rounded-t-[32px] border border-slate-200 bg-white shadow-2xl dark:border-white/10 dark:bg-slate-950">
          <div className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-slate-100 bg-white/95 px-4 py-3 backdrop-blur dark:border-white/10 dark:bg-slate-950/95">
            <div className="h-1.5 w-12 rounded-full bg-slate-200 dark:bg-white/20" aria-hidden="true" />
            <h2 className="sr-only">{title}</h2>
            <button ref={closeButtonRef} type="button" className="grid h-10 w-10 place-items-center rounded-2xl border border-slate-200 text-slate-700 dark:border-white/10 dark:text-white" onClick={onClose} aria-label={closeLabel}>
              <X className="h-4 w-4" />
            </button>
          </div>
          <div data-bottom-sheet-content className="max-h-[calc(min(88dvh,760px)-4.25rem)] overflow-y-auto overflow-x-hidden px-4 pb-[calc(env(safe-area-inset-bottom)+1rem)] pt-4">
            {children}
          </div>
        </section>
      </div>
    </Portal>
  );
}
