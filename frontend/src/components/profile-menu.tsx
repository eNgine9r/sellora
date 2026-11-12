"use client";

import { useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import { ChevronDown, LogOut, Settings, Users } from "lucide-react";
import { Portal } from "@/components/ui/portal";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { useI18n } from "@/i18n/provider";
import { CurrentUser, WorkspaceMembership } from "@/types/auth";

function userName(user: CurrentUser | null) {
  const name = [user?.first_name, user?.last_name].filter(Boolean).join(" ").trim();
  return name || user?.email || "Sellora";
}

export function ProfileMenu({ currentUser, currentWorkspace, currentWorkspaceId, memberships, onLogout, onSwitchWorkspace, onWorkspaceCreated }: { currentUser: CurrentUser | null; currentWorkspace: WorkspaceMembership | null; currentWorkspaceId: string | null; memberships: WorkspaceMembership[]; onLogout: () => void; onSwitchWorkspace: (workspaceId: string) => void; onWorkspaceCreated: () => Promise<void> }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({ top: 72, right: 24 });
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;
    const rect = triggerRef.current?.getBoundingClientRect();
    if (rect) {
      setPosition({ top: Math.min(rect.bottom + 10, window.innerHeight - 24), right: Math.max(window.innerWidth - rect.right, 12) });
    }
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (panelRef.current?.contains(target) || triggerRef.current?.contains(target)) return;
      setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <>
      <button
        ref={triggerRef}
        title={userName(currentUser)}
        type="button"
        className="account-profile-trigger hidden h-10 min-w-10 max-w-[220px] shrink-0 items-center gap-2 rounded-xl border border-border-subtle bg-surface-2 px-1.5 text-left text-text-primary transition hover:border-border-strong hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring md:flex xl:px-2"
        aria-label={t("accountMenu.profile")}
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-primary/15 text-xs font-semibold text-primary">{userName(currentUser).slice(0, 1).toUpperCase()}</span>
        <span className="hidden min-w-0 leading-tight xl:block">
          <span className="block truncate text-xs font-semibold text-text-primary">{userName(currentUser)}</span>
          <span className="block truncate text-[11px] text-text-muted">{currentWorkspace?.workspace_name ?? t("accountMenu.workspace")}</span>
        </span>
        <ChevronDown className="hidden h-3.5 w-3.5 shrink-0 text-text-muted xl:block" />
      </button>
      {open ? (
        <Portal>
          <div
            ref={panelRef}
            id={menuId}
            className="fixed z-[100] max-h-[min(82vh,720px)] w-[min(calc(100vw-1.5rem),348px)] overflow-y-auto overflow-x-hidden rounded-2xl border border-border-subtle bg-surface-1 p-3 text-text-primary shadow-2xl sm:p-4"
            style={{ top: position.top, right: position.right }}
            role="menu"
          >
            <section className="rounded-3xl bg-slate-50 p-4 dark:bg-white/5" aria-label={t("accountMenu.user")}> 
              <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">{t("accountMenu.user")}</p>
              <p className="mt-2 truncate text-lg font-black">{userName(currentUser)}</p>
              <p className="truncate text-sm text-slate-500 dark:text-slate-400">{currentUser?.email}</p>
            </section>
            <div className="mt-4">
              <WorkspaceSwitcher memberships={memberships} currentWorkspaceId={currentWorkspaceId} onSwitchWorkspace={onSwitchWorkspace} onCreated={onWorkspaceCreated} onClose={() => setOpen(false)} />
            </div>
            <section className="mt-4 grid gap-2 border-t border-slate-100 pt-4 dark:border-white/10" aria-label={t("accountMenu.settings")}> 
              <p className="px-1 text-xs font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">{t("accountMenu.settings")}</p>
              <Link className="flex min-h-11 items-center gap-3 rounded-2xl px-3 text-sm font-bold hover:bg-slate-50 dark:hover:bg-white/10" href="/settings/workspace" onClick={() => setOpen(false)} role="menuitem">
                <Settings className="h-4 w-4" /> {t("accountMenu.workspace")}
              </Link>
              <Link className="flex min-h-11 items-center gap-3 rounded-2xl px-3 text-sm font-bold hover:bg-slate-50 dark:hover:bg-white/10" href="/settings/team" onClick={() => setOpen(false)} role="menuitem">
                <Users className="h-4 w-4" /> {t("accountMenu.team")}
              </Link>
            </section>
            <button className="mt-4 flex min-h-11 w-full items-center gap-3 rounded-2xl border border-red-100 bg-red-50 px-3 text-left text-sm font-black text-red-700 transition hover:bg-red-100 dark:border-red-400/20 dark:bg-red-500/10 dark:text-red-200" type="button" onClick={() => { setOpen(false); onLogout(); }} role="menuitem">
              <LogOut className="h-4 w-4" /> {t("actions.logout")}
            </button>
          </div>
        </Portal>
      ) : null}
    </>
  );
}
