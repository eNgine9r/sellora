"use client";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AdvertisingTrendPoint } from "@/types/advertising";
export function AdvertisingTrendChart({ data }: { data: AdvertisingTrendPoint[] }) { return <section className="rounded-2xl bg-white p-4 shadow-sm"><h2 className="text-lg font-semibold">Revenue vs Spend Trend</h2><div className="mt-4 h-72"><ResponsiveContainer width="100%" height="100%"><LineChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="date" /><YAxis /><Tooltip /><Line type="monotone" dataKey="spend" stroke="#f97316" /><Line type="monotone" dataKey="revenue" stroke="#16a34a" /><Line type="monotone" dataKey="roas" stroke="#2563eb" /></LineChart></ResponsiveContainer></div></section>; }
