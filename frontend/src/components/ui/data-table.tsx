import type { ReactNode } from "react";
import { cn } from "@/services/utils";
import { EmptyState } from "@/components/ui/states";

export type DataTableColumn<T> = {
  key: string;
  header: ReactNode;
  cell: (row: T) => ReactNode;
  className?: string;
};

export function DataTable<T>({ columns, rows, getRowKey, emptyTitle = "Даних ще немає", emptyDescription = "Коли записи зʼявляться, вони будуть показані в цій таблиці.", className }: { columns: DataTableColumn<T>[]; rows: T[]; getRowKey: (row: T, index: number) => string; emptyTitle?: string; emptyDescription?: string; className?: string }) {
  if (!rows.length) return <EmptyState title={emptyTitle} description={emptyDescription} />;

  return (
    <div className={cn("sellora-scrollbar overflow-x-auto rounded-[var(--radius-card)] border border-border bg-card shadow-sellora-sm", className)}>
      <table className="min-w-full text-left text-sm">
        <thead className="bg-muted/70 text-xs font-black uppercase tracking-wide text-muted-foreground">
          <tr>{columns.map((column) => <th key={column.key} className={cn("whitespace-nowrap px-4 py-3", column.className)}>{column.header}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((row, index) => (
            <tr key={getRowKey(row, index)} className="transition hover:bg-muted/50">
              {columns.map((column) => <td key={column.key} className={cn("px-4 py-3 align-middle text-foreground", column.className)}>{column.cell(row)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
