"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatMoney } from "@/lib/currency";

type DailyPoint = {
  date: string;
  revenueNumber: number;
  profitNumber: number | null;
  ordersCount: number;
};

export function SalesProfitChart({ trend, currencyCode, revenueLabel, profitLabel }: {
  trend: DailyPoint[];
  currencyCode: string;
  revenueLabel: string;
  profitLabel: string;
}) {
  return <div className="h-52 min-w-0 sm:h-60" data-dashboard-lazy-chart="sales">
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={trend} margin={{ top: 8, left: -12, right: 8, bottom: 2 }}>
        <defs>
          <linearGradient id="selloraRevenue" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="var(--primary-hover)" stopOpacity={0.3} />
            <stop offset="95%" stopColor="var(--primary-hover)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 5" vertical={false} />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--text-secondary)" }} tickLine={false} axisLine={false} minTickGap={28} />
        <YAxis tick={{ fontSize: 11, fill: "var(--text-secondary)" }} tickLine={false} axisLine={false} width={45} />
        <Tooltip contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border-default)", borderRadius: 12, color: "var(--text-primary)" }} formatter={(value) => formatMoney(Number(value), currencyCode)} />
        <Area type="monotone" dataKey="revenueNumber" name={revenueLabel} stroke="var(--primary-hover)" fill="url(#selloraRevenue)" strokeWidth={2.5} activeDot={{ r: 5 }} />
        <Area type="monotone" dataKey="profitNumber" name={profitLabel} stroke="var(--success)" fill="transparent" strokeWidth={2.5} activeDot={{ r: 5 }} />
      </AreaChart>
    </ResponsiveContainer>
  </div>;
}
