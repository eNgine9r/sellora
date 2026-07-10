"use client";

import { ReactNode, useEffect, useRef } from "react";
import { X } from "lucide-react";
import { Button, IconButton } from "@/components/ui/primitives";
import { useI18n } from "@/i18n/provider";

export function useOverlayLifecycle(open: boolean, onClose: () => void) {
  const panelRef = useRef<HTMLDivElement>(null);
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
    return () => { window.clearTimeout(id); document.body.style.overflow = previousOverflow; document.removeEventListener("keydown", onKeyDown); previousFocus.current?.focus?.(); };
  }, [open, onClose]);
  return panelRef;
}

export function Drawer({ open, title, description, children, footer, onClose }: { open: boolean; title: string; description?: string; children: ReactNode; footer?: ReactNode; onClose: () => void }) {
  const { t } = useI18n();
  const panelRef = useOverlayLifecycle(open, onClose);
  if (!open) return null;
  return <div className="fixed inset-0 z-[var(--z-overlay)]" role="dialog" aria-modal="true" aria-labelledby="sellora-drawer-title"><button className="absolute inset-0 bg-[var(--overlay-background)] backdrop-blur-sm" aria-label={t("actions.close")} onClick={onClose} /><div ref={panelRef} tabIndex={-1} className="absolute inset-y-0 right-0 flex h-dvh w-full max-w-full flex-col border-l border-border-subtle bg-surface-1 shadow-[var(--shadow-overlay)] outline-none md:w-[min(520px,calc(100vw-32px))]"><header className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-border-subtle bg-surface-1/95 p-5 backdrop-blur"><div><h2 id="sellora-drawer-title" className="text-xl font-black text-text-primary">{title}</h2>{description ? <p className="mt-1 text-sm leading-6 text-text-secondary">{description}</p> : null}</div><IconButton variant="ghost" onClick={onClose} aria-label={t("actions.close")}><X className="h-5 w-5" /></IconButton></header><div className="sellora-scrollbar min-h-0 flex-1 overflow-y-auto p-5">{children}</div>{footer ? <footer className="sticky bottom-0 border-t border-border-subtle bg-surface-1/95 p-4 backdrop-blur">{footer}</footer> : null}</div></div>;
}

export function Modal({ open, title, description, children, onClose }: { open: boolean; title: string; description?: string; children: ReactNode; onClose: () => void }) {
  const panelRef = useOverlayLifecycle(open, onClose);
  if (!open) return null;
  return <div className="fixed inset-0 z-[var(--z-overlay)] overflow-y-auto p-4" role="dialog" aria-modal="true" aria-labelledby="sellora-modal-title"><button className="fixed inset-0 bg-[var(--overlay-background)] backdrop-blur-sm" aria-label="Close" onClick={onClose} /><div className="relative mx-auto flex min-h-full max-w-lg items-center justify-center"><section ref={panelRef} tabIndex={-1} className="w-full rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-5 shadow-[var(--shadow-overlay)] outline-none"><h2 id="sellora-modal-title" className="text-xl font-black text-text-primary">{title}</h2>{description ? <p className="mt-2 text-sm leading-6 text-text-secondary">{description}</p> : null}<div className="mt-5">{children}</div></section></div></div>;
}

export function ConfirmationDialog({ open, title, description, actionLabel, isSubmitting, error, onCancel, onConfirm }: { open: boolean; title: string; description: string; actionLabel: string; isSubmitting?: boolean; error?: string | null; onCancel: () => void; onConfirm: () => void }) {
  return <Modal open={open} title={title} description={description} onClose={onCancel}>{error ? <p className="mb-4 rounded-2xl border border-danger/25 bg-[var(--danger-surface)] px-3 py-2 text-sm font-bold text-[var(--danger-foreground)]">{error}</p> : null}<div className="grid gap-3 sm:grid-cols-2"><Button variant="secondary" onClick={onCancel} disabled={isSubmitting}>Скасувати</Button><Button variant="danger" onClick={onConfirm} loading={isSubmitting}>{actionLabel}</Button></div></Modal>;
}
