"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

type StatusPoint = {
  name: string;
  label: string;
  value: number;
  percent: number;
  color: string;
};

export function OrderStatusChart({ statuses }: { statuses: StatusPoint[] }) {
  return <div className="grid gap-2" data-dashboard-lazy-chart="statuses">
    <div className="h-40 min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={statuses} dataKey="value" nameKey="label" innerRadius={48} outerRadius={69} paddingAngle={3}>
            {statuses.map((entry) => <Cell key={entry.name} fill={entry.color} />)}
          </Pie>
          <Tooltip contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border-default)", borderRadius: 12, color: "var(--text-primary)" }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
    <div className="grid gap-1">
      {statuses.map((status) => <div key={status.name} className="flex items-center justify-between gap-3 rounded-lg px-2 py-1 text-xs text-text-secondary">
        <span className="flex min-w-0 items-center gap-2 truncate"><span aria-hidden="true" className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: status.color }} />{status.label}</span>
        <strong className="shrink-0 font-semibold tabular-nums text-text-primary">{status.value} · {status.percent}%</strong>
      </div>)}
    </div>
  </div>;
}
