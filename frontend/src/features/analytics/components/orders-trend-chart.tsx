"use client";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { SalesTrendItem } from "@/types/analytics";
export function OrdersTrendChart({ data }: { data: SalesTrendItem[] }) { return <div className="h-64 rounded-xl bg-white p-4 shadow-sm"><h3 className="mb-3 font-semibold">Orders Trend</h3><ResponsiveContainer width="100%" height="85%"><BarChart data={data}><XAxis dataKey="date" /><YAxis /><Tooltip /><Bar dataKey="orders_count" fill="#7c3aed" /></BarChart></ResponsiveContainer></div>; }
