"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Command, LoaderCircle, Search, X } from "lucide-react";
import { Portal } from "@/components/ui/portal";
import { useI18n } from "@/i18n/provider";
import { GlobalSearchKind, searchWorkspaceRecords } from "@/services/global-search";

const kinds: GlobalSearchKind[] = ["orders", "customers", "leads", "products", "shipments"];

const quickRoutes = [
  { href: "/orders", kind: "orders" },
  { href: "/customers", kind: "customers" },
  { href: "/products", kind: "products" },
  { href: "/shipments", kind: "shipments" },
] as const;

export function GlobalSearch({ workspaceId }: { workspaceId: string | null }) {
  const { t } = useI18n();
  const router = useRouter();
  const pathname = usePathname();
  const inputId = useId();
  const panelId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      const element = event.target as HTMLElement | null;
      const typing = element?.matches("input,textarea,select,[contenteditable='true']");
      const anotherDialog = !open && document.querySelector('[role="dialog"][aria-modal="true"]');
      if (anotherDialog) return;
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        if (workspaceId) {
          if (open) { setOpen(false); window.requestAnimationFrame(() => triggerRef.current?.focus()); }
          else setOpen(true);
        }
      } else if (event.key === "/" && !typing && !event.altKey && !event.ctrlKey && !event.metaKey) {
        event.preventDefault();
        if (workspaceId) setOpen(true);
      }
    };
    document.addEventListener("keydown", shortcut);
    return () => document.removeEventListener("keydown", shortcut);
  }, [workspaceId, open]);

  useEffect(() => {
    setOpen(false);
    setQuery("");
    setDebounced("");
    setActiveIndex(0);
  }, [pathname, workspaceId]);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebounced(query.trim().slice(0, 80)), 280);
    return () => window.clearTimeout(timeout);
  }, [query]);

  const readyToSearch = open && Boolean(workspaceId) && debounced.length >= 2;
  const resultsQuery = useQuery({
    queryKey: ["global-search", workspaceId, debounced],
    queryFn: ({ signal }) => searchWorkspaceRecords(workspaceId!, debounced, signal),
    enabled: readyToSearch,
    staleTime: 20_000, gcTime: 60_000,
    retry: 1, refetchOnWindowFocus: false,
  });
  const fresh = query.trim().slice(0, 80) === debounced;
  const results = useMemo(() => readyToSearch && fresh ? resultsQuery.data ?? [] : [], [readyToSearch, fresh, resultsQuery.data]);
  const grouped = useMemo(() => kinds.map((kind) => ({
    kind, items: results.map((item, index) => ({ item, index })).filter(({ item }) => item.kind === kind),
  })).filter((group) => group.items.length), [results]);

  useEffect(() => { setActiveIndex(0); }, [debounced]);

  const dismiss = () => {
    setOpen(false);
    setQuery("");
    setDebounced("");
    setActiveIndex(0);
    window.requestAnimationFrame(() => triggerRef.current?.focus());
  };

  const navigate = (href: string) => {
    setOpen(false);
    setQuery("");
    router.push(href);
  };

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    inputRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); dismiss(); return; }
      if (event.key !== "Tab") return;
      const elements = [...(panelRef.current?.querySelectorAll<HTMLElement>("button:not(:disabled),a[href],input:not(:disabled)") ?? [])];
      if (!elements.length) return;
      const first = elements[0], last = elements[elements.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => { document.body.style.overflow = previous; document.removeEventListener("keydown", onKeyDown); };
  }, [open]);

  const onSearchKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown" && results.length) {
      event.preventDefault();
      setActiveIndex((index) => Math.min(results.length - 1, index + 1));
    } else if (event.key === "ArrowUp" && results.length) {
      event.preventDefault();
      setActiveIndex((index) => Math.max(0, index - 1));
    } else if (event.key === "Enter" && results[activeIndex]) {
      event.preventDefault();
      navigate(results[activeIndex].href);
    }
  };

  return (
    <>
      <button ref={triggerRef} type="button" disabled={!workspaceId}
        onClick={() => setOpen(true)} aria-label={t("topbar.search.open")} aria-keyshortcuts="Control+K Meta+K"
        data-global-search-trigger
        className="group hidden min-h-10 min-w-[190px] max-w-[560px] flex-1 items-center gap-2.5 rounded-xl border border-border-subtle bg-surface-2/75 px-3 text-left text-sm text-text-muted transition hover:border-border-strong hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring disabled:opacity-40 md:flex">
        <Search aria-hidden="true" className="h-4 w-4 shrink-0 text-text-muted group-hover:text-primary" />
        <span className="min-w-0 flex-1 truncate">{t("topbar.searchPlaceholder")}</span>
        <kbd className="hidden shrink-0 rounded-md border border-border-subtle bg-surface-1 px-1.5 py-0.5 text-[10px] font-medium text-text-muted xl:inline-flex">Ctrl K</kbd>
      </button>
      <button type="button" disabled={!workspaceId} onClick={() => setOpen(true)}
        aria-label={t("topbar.search.open")} data-global-search-mobile
        className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-border-subtle bg-surface-2 text-text-secondary transition hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring disabled:opacity-40 md:hidden">
        <Search aria-hidden="true" className="h-[19px] w-[19px]" />
      </button>

      {open ? <Portal>
        <div className="fixed inset-0 z-[120] flex items-start justify-center overflow-y-auto bg-[var(--overlay-background)] px-3 pb-5 pt-[max(1rem,env(safe-area-inset-top))] backdrop-blur-sm sm:pt-[min(14vh,120px)]"
          role="presentation" data-global-search-overlay onMouseDown={(event) => { if (event.target === event.currentTarget) dismiss(); }}>
          <div ref={panelRef} role="dialog" aria-modal="true" aria-label={t("topbar.search.title")}
            className="flex max-h-[min(85dvh,720px)] w-full max-w-[620px] min-w-0 flex-col overflow-hidden rounded-2xl border border-border-subtle bg-surface-1 shadow-2xl sm:rounded-[22px]">
            <div className="flex min-h-14 items-center gap-3 border-b border-border-subtle px-4">
              <Search aria-hidden="true" className="h-5 w-5 shrink-0 text-primary" />
              <input ref={inputRef} id={inputId} type="search" role="combobox" aria-autocomplete="list" aria-expanded={Boolean(results.length)}
                aria-controls={panelId} aria-activedescendant={results[activeIndex] ? `${panelId}-${activeIndex}` : undefined}
                value={query} onChange={(event) => setQuery(event.target.value.slice(0, 80))}
                onKeyDown={onSearchKeyDown} autoComplete="off" spellCheck={false}
                placeholder={t("topbar.searchPlaceholder")}
                className="h-12 w-full min-w-0 flex-1 bg-transparent text-base text-text-primary outline-none placeholder:text-text-muted" />
              {query ? <button type="button" className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-text-muted hover:bg-surface-hover" onClick={() => { setQuery(""); inputRef.current?.focus(); }} aria-label={t("topbar.search.clear")}><X className="h-4 w-4" /></button> : null}
              <button type="button" onClick={dismiss} aria-label={t("actions.close")}
                className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-border-subtle text-text-secondary hover:bg-surface-hover"><X className="h-4 w-4" /></button>
            </div>

            <div className="min-h-0 overflow-y-auto overscroll-contain p-2 sm:p-3" id={panelId} role={query.trim().length >= 2 ? "listbox" : undefined} aria-label={t("topbar.search.title")} aria-busy={readyToSearch && (!fresh || resultsQuery.isFetching)}>
              {query.trim().length < 2 ? <>
                <p className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-text-muted">{t("topbar.search.quick")}</p>
                <nav aria-label={t("topbar.search.quick")} className="grid grid-cols-2 gap-2">
                  {quickRoutes.map(({ kind, href }) => <button type="button" key={href} onClick={() => navigate(href)}
                    className="flex min-h-11 min-w-0 items-center justify-between gap-2 rounded-xl border border-border-subtle bg-surface-2 px-3 text-left text-xs font-medium text-text-primary hover:border-primary/30 hover:bg-surface-hover">
                    <span className="truncate">{t(`topbar.search.groups.${kind}`)}</span><ArrowRight aria-hidden="true" className="h-3.5 w-3.5 shrink-0 text-text-muted" />
                  </button>)}
                </nav>
                <p className="px-3 pb-2 pt-4 text-xs text-text-muted">{t("topbar.search.hint")}</p>
              </> : !fresh || resultsQuery.isPending ? (
                <div role="status" className="flex min-h-24 items-center justify-center gap-2 text-sm text-text-muted">
                  <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin motion-reduce:animate-none" />{t("topbar.search.loading")}
                </div>
              ) : resultsQuery.isError ? (
                <div role="status" className="grid min-h-24 place-content-center gap-2 text-center text-sm text-text-secondary">
                  <span>{t("topbar.search.error")}</span>
                  <button type="button" onClick={() => void resultsQuery.refetch()} className="text-xs font-semibold text-primary">{t("topbar.search.retry")}</button>
                </div>
              ) : !results.length ? <p role="status" className="p-6 text-center text-sm text-text-muted">{t("topbar.search.empty")}</p> : (
                grouped.map(({ kind, items }) => <section key={kind} role="group" aria-label={t(`topbar.search.groups.${kind}`)} className="mb-2 last:mb-0">
                  <h3 className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-text-muted">{t(`topbar.search.groups.${kind}`)}</h3>
                  {items.map(({ item, index }) => <button key={item.kind + item.id} type="button" id={`${panelId}-${index}`}
                    role="option" aria-selected={activeIndex === index} onMouseEnter={() => setActiveIndex(index)}
                    onClick={() => navigate(item.href)}
                    className={`flex min-h-12 w-full min-w-0 items-center gap-3 rounded-xl px-3 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring ${activeIndex === index ? "bg-surface-selected" : "hover:bg-surface-hover"}`}>
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-primary/10 text-[11px] font-semibold text-primary" aria-hidden="true">{t(`topbar.search.groups.${kind}`).slice(0, 1)}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-text-primary">{item.title}</span>
                      {item.subtitle ? <span className="block truncate text-xs text-text-secondary">{item.kind === "orders" ? t(`statuses.order.${item.subtitle}`) : item.subtitle}</span> : null}
                    </span>
                    <ArrowRight aria-hidden="true" className="h-4 w-4 shrink-0 text-text-muted" />
                  </button>)}
                </section>)
              )}
            </div>
            <div className="hidden items-center gap-3 border-t border-border-subtle bg-surface-2/50 px-4 py-2 text-[11px] text-text-muted sm:flex">
              <Command aria-hidden="true" className="h-3.5 w-3.5" />
              <span>{t("topbar.search.keyboard")}</span>
            </div>
          </div>
        </div>
      </Portal> : null}
    </>
  );
}
