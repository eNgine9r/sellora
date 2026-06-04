"use client";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { SalesTrendItem } from "@/types/analytics";
export function ProfitTrendChart({ data }: { data: SalesTrendItem[] }) { return <div className="h-64 rounded-xl bg-white p-4 shadow-sm"><h3 className="mb-3 font-semibold">Profit Trend</h3><ResponsiveContainer width="100%" height="85%"><LineChart data={data}><XAxis dataKey="date" /><YAxis /><Tooltip /><Line type="monotone" dataKey="net_profit" stroke="#16a34a" strokeWidth={2} /></LineChart></ResponsiveContainer></div>; }
