import type { Key, ReactNode } from "react";

export type ReportTableColumn<Row> = {
  key: string;
  label: string;
  render: (row: Row) => ReactNode;
  emphasis?: boolean;
};

type Props<Row> = {
  rows: readonly Row[];
  columns: readonly ReportTableColumn<Row>[];
  rowKey: (row: Row, index: number) => Key;
  empty?: ReactNode;
  wide?: boolean;
  className?: string;
};

/**
 * Consistent read-only report presentation for Sellora CRM/ERP.
 * Uses the same container-width table/card breakpoint as operational lists.
 * A table remains visible on wide panels; mobile/narrow panes get labeled cards,
 * preserving metric names instead of requiring a nested horizontal scrollbar.
 * RBAC-sensitive columns must be omitted by the caller before passing columns.
 */
export function ResponsiveReportTable<Row>({
  rows,
  columns,
  rowKey,
  empty,
  wide = false,
  className = "",
}: Props<Row>) {
  return (
    <div
      className={`sellora-adaptive-list min-w-0 max-w-full ${wide ? "sellora-adaptive-wide-list" : ""} ${className}`}
      data-sellora-report-table
    >
      {rows.length ? (
        <>
          <div className="sellora-adaptive-table min-w-0 w-full">
            <table className="w-full table-fixed text-left text-sm text-text-secondary">
              <thead className="border-b border-border-subtle bg-surface-2 text-xs font-bold text-text-muted">
                <tr>{columns.map((column) => <th key={column.key} scope="col" className="min-w-0 break-words px-3 py-3 text-left">{column.label}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {rows.map((row, index) => (
                  <tr key={rowKey(row, index)} className="align-top transition-colors hover:bg-surface-hover">
                    {columns.map((column) => (
                      <td key={column.key} className={`min-w-0 px-3 py-3 align-top ${column.emphasis ? "font-semibold text-text-primary" : ""}`}>
                        <div className="min-w-0 break-words [overflow-wrap:anywhere]">{column.render(row)}</div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="sellora-adaptive-cards min-w-0 gap-3">
            {rows.map((row, index) => (
              <article key={rowKey(row, index)} className="min-w-0 rounded-2xl border border-border-subtle bg-surface-1 p-3 shadow-sm">
                <dl className="grid min-w-0 gap-2 text-sm">
                  {columns.map((column) => (
                    <div key={column.key} className="grid min-w-0 grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] items-start gap-3">
                      <dt className="min-w-0 break-words text-xs text-text-muted">{column.label}</dt>
                      <dd className={`min-w-0 break-words text-right [overflow-wrap:anywhere] ${column.emphasis ? "font-semibold text-text-primary" : "text-text-secondary"}`}>{column.render(row)}</dd>
                    </div>
                  ))}
                </dl>
              </article>
            ))}
          </div>
        </>
      ) : empty ? (
        <div className="min-w-0">{empty}</div>
      ) : (
        <p className="rounded-xl border border-dashed border-border-subtle p-4 text-sm text-text-muted">—</p>
      )}
    </div>
  );
}
