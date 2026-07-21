"use client";

import { ReactNode, useEffect, useId, useRef } from "react";
import { X } from "lucide-react";
import { Button, IconButton } from "@/components/ui/primitives";
import { Portal } from "@/components/ui/portal";
import { useI18n } from "@/i18n/provider";

type OverlaySize = "sm" | "md" | "lg" | "xl";
const modalSizeClass: Record<OverlaySize, string> = {
  sm: "max-w-[420px]",
  md: "max-w-[560px]",
  lg: "max-w-[720px]",
  xl: "max-w-[900px]",
};

export function useOverlayLifecycle(open: boolean, onClose: () => void) {
  const panelRef = useRef<HTMLElement | null>(null);
  const previousFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    previousFocus.current = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const id = window.setTimeout(() => panelRef.current?.focus(), 0);
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = panelRef.current.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])');
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      window.clearTimeout(id);
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
      previousFocus.current?.focus?.();
    };
  }, [open, onClose]);

  return panelRef;
}

export function Drawer({ open, title, description, children, footer, onClose }: { open: boolean; title: string; description?: string; children: ReactNode; footer?: ReactNode; onClose: () => void }) {
  const { t } = useI18n();
  const titleId = useId();
  const panelRef = useOverlayLifecycle(open, onClose);
  if (!open) return null;

  return (
    <Portal>
      <div className="fixed inset-0 z-[var(--z-overlay)]" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <button className="absolute inset-0 bg-[var(--overlay-background)] backdrop-blur-sm" aria-label={t("actions.close")} onClick={onClose} />
        <section ref={panelRef} tabIndex={-1} className="sellora-dialog-panel absolute inset-x-0 bottom-0 flex max-h-[96dvh] min-h-0 flex-col overflow-hidden rounded-t-[28px] border border-b-0 border-border-subtle bg-surface-1 shadow-[var(--shadow-overlay)] outline-none sm:inset-y-4 sm:left-auto sm:right-4 sm:h-auto sm:max-h-[calc(100dvh-2rem)] sm:w-[min(520px,calc(100vw-2rem))] sm:rounded-[var(--radius-shell)] sm:border md:inset-y-0 md:right-0 md:h-dvh md:max-h-dvh md:rounded-none md:border-y-0 md:border-r-0">
          <header className="sticky top-0 z-10 flex min-w-0 items-start justify-between gap-3 border-b border-border-subtle bg-surface-1/95 px-4 pb-4 pt-[max(1rem,env(safe-area-inset-top))] backdrop-blur sm:p-5">
            <div className="min-w-0"><h2 id={titleId} className="break-words text-xl font-black text-text-primary">{title}</h2>{description ? <p className="mt-1 break-words text-sm leading-6 text-text-secondary">{description}</p> : null}</div>
            <IconButton variant="ghost" onClick={onClose} aria-label={t("actions.close")}><X className="h-5 w-5" /></IconButton>
          </header>
          <div className="sellora-scrollbar min-h-0 min-w-0 flex-1 overflow-x-hidden overflow-y-auto overscroll-contain p-4 sm:p-5">{children}</div>
          {footer ? <footer className="sticky bottom-0 grid gap-2 border-t border-border-subtle bg-surface-1/95 px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-4 backdrop-blur sm:flex sm:justify-end sm:p-4 [&>*]:w-full sm:[&>*]:w-auto">{footer}</footer> : null}
        </section>
      </div>
    </Portal>
  );
}

export function Modal({ open, title, description, children, onClose, size = "md" }: { open: boolean; title: string; description?: string; children: ReactNode; onClose: () => void; size?: OverlaySize }) {
  const { t } = useI18n();
  const titleId = useId();
  const panelRef = useOverlayLifecycle(open, onClose);
  if (!open) return null;

  return (
    <Portal>
      <div className="fixed inset-0 z-[var(--z-overlay)] flex items-end justify-center overflow-hidden sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <button className="absolute inset-0 bg-[var(--overlay-background)] backdrop-blur-sm" aria-label={t("actions.close")} onClick={onClose} />
        <section ref={panelRef} tabIndex={-1} className={`sellora-dialog-panel relative flex max-h-[96dvh] w-full ${modalSizeClass[size]} min-w-0 flex-col overflow-hidden rounded-t-[28px] border border-b-0 border-border-subtle bg-surface-1 shadow-[var(--shadow-overlay)] outline-none sm:max-h-[calc(100dvh-2rem)] sm:rounded-[var(--radius-shell)] sm:border`}>
          <header className="flex min-w-0 items-start justify-between gap-3 border-b border-border-subtle bg-surface-1/95 px-4 pb-4 pt-[max(1rem,env(safe-area-inset-top))] backdrop-blur sm:p-5">
            <div className="min-w-0"><h2 id={titleId} className="break-words text-xl font-black text-text-primary">{title}</h2>{description ? <p className="mt-1 break-words text-sm leading-6 text-text-secondary">{description}</p> : null}</div>
            <IconButton variant="ghost" onClick={onClose} aria-label={t("actions.close")}><X className="h-5 w-5" /></IconButton>
          </header>
          <div className="sellora-scrollbar min-h-0 min-w-0 flex-1 overflow-x-hidden overflow-y-auto overscroll-contain px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-4 sm:p-5">{children}</div>
        </section>
      </div>
    </Portal>
  );
}

export function ConfirmationDialog({ open, title, description, actionLabel, isSubmitting, error, onCancel, onConfirm }: { open: boolean; title: string; description: string; actionLabel: string; isSubmitting?: boolean; error?: string | null; onCancel: () => void; onConfirm: () => void }) {
  const { t } = useI18n();
  return <Modal open={open} title={title} description={description} onClose={onCancel} size="sm">{error ? <p className="mb-4 rounded-2xl border border-danger/25 bg-[var(--danger-surface)] px-3 py-2 text-sm font-bold text-[var(--danger-foreground)]">{error}</p> : null}<div className="grid gap-3 sm:grid-cols-2"><Button variant="secondary" onClick={onCancel} disabled={isSubmitting}>{t("actions.cancel")}</Button><Button variant="danger" onClick={onConfirm} loading={isSubmitting}>{actionLabel}</Button></div></Modal>;
}
