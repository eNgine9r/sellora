"use client";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { SalesTrendItem } from "@/types/analytics";
export function RevenueTrendChart({ data }: { data: SalesTrendItem[] }) { return <div className="h-64 rounded-xl bg-white p-4 shadow-sm"><h3 className="mb-3 font-semibold">Revenue Trend</h3><ResponsiveContainer width="100%" height="85%"><LineChart data={data}><XAxis dataKey="date" /><YAxis /><Tooltip /><Line type="monotone" dataKey="revenue" stroke="#2563eb" strokeWidth={2} /></LineChart></ResponsiveContainer></div>; }
