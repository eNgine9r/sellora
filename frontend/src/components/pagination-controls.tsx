"use client";

import { useI18n } from "@/i18n/provider";

export const PAGE_SIZE_OPTIONS = [5, 15, 30] as const;

type PaginationControlsProps = {
  page: number;
  pageSize: number;
  totalItems: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
};

function pageNumbers(currentPage: number, totalPages: number) {
  const pages = new Set<number>([1, totalPages, currentPage, currentPage - 1, currentPage + 1]);
  if (currentPage <= 3) [2, 3, 4].forEach((page) => pages.add(page));
  if (currentPage >= totalPages - 2) [totalPages - 3, totalPages - 2, totalPages - 1].forEach((page) => pages.add(page));
  return [...pages].filter((page) => page >= 1 && page <= totalPages).sort((a, b) => a - b);
}

export function clampPage(page: number, pageSize: number, totalItems: number) {
  return Math.min(Math.max(1, page), Math.max(1, Math.ceil(totalItems / pageSize)));
}

export function paginateItems<T>(items: T[], page: number, pageSize: number) {
  const safePage = clampPage(page, pageSize, items.length);
  const start = (safePage - 1) * pageSize;
  return items.slice(start, start + pageSize);
}

export function PaginationControls({ page, pageSize, totalItems, onPageChange, onPageSizeChange }: PaginationControlsProps) {
  const { t } = useI18n();
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const safePage = clampPage(page, pageSize, totalItems);
  const firstItem = totalItems === 0 ? 0 : (safePage - 1) * pageSize + 1;
  const lastItem = Math.min(totalItems, safePage * pageSize);
  const pages = pageNumbers(safePage, totalPages);

  return (
    <nav className="flex min-w-0 flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-3 text-sm shadow-sm dark:border-white/10 dark:bg-slate-900 sm:flex-row sm:items-center sm:justify-between" aria-label={t("pagination.page")}>
      <div className="flex min-w-0 flex-col gap-1 text-slate-600 dark:text-slate-300 sm:flex-row sm:items-center sm:gap-3">
        <label className="flex items-center gap-2 font-semibold">
          {t("pagination.show")}
          <select className="min-h-10 rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-white/10 dark:bg-slate-950" value={pageSize} onChange={(event) => onPageSizeChange(Number(event.target.value))}>
            {PAGE_SIZE_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
        </label>
        <span>{t("pagination.showing")} {firstItem}-{lastItem} {t("pagination.of")} {totalItems} {t("pagination.results")}</span>
      </div>
      <div className="sellora-scrollbar flex min-w-0 max-w-full items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
        <button className="min-h-10 shrink-0 rounded-lg border border-slate-300 px-3 py-2 font-bold disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/10" disabled={safePage <= 1} type="button" onClick={() => onPageChange(safePage - 1)}>{t("pagination.previous")}</button>
        {pages.map((pageNumber, index) => (
          <span className="flex items-center gap-2" key={pageNumber}>
            {index > 0 && pageNumber - pages[index - 1] > 1 ? <span className="text-slate-400">…</span> : null}
            <button className={`min-h-10 min-w-10 shrink-0 rounded-lg border px-3 py-2 font-bold ${pageNumber === safePage ? "border-blue-600 bg-blue-600 text-white" : "border-slate-300 dark:border-white/10"}`} type="button" aria-current={pageNumber === safePage ? "page" : undefined} onClick={() => onPageChange(pageNumber)}>{pageNumber}</button>
          </span>
        ))}
        <button className="min-h-10 shrink-0 rounded-lg border border-slate-300 px-3 py-2 font-bold disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/10" disabled={safePage >= totalPages} type="button" onClick={() => onPageChange(safePage + 1)}>{t("pagination.next")}</button>
      </div>
    </nav>
  );
}
