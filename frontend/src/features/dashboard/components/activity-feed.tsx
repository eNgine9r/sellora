export function ActivityFeed() {
  const events = ["Lead converted to order", "Shipment marked in transit", "Ad metric added manually", "Inventory reserved for order"];
  return <section className="rounded-[20px] border border-slate-100 bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.06)]"><h2 className="text-lg font-black">Activity</h2><div className="mt-4 grid gap-4">{events.map((event) => <div key={event} className="flex gap-3"><span className="mt-1 h-2.5 w-2.5 rounded-full bg-violet-600" /><div><p className="text-sm font-semibold text-slate-800">{event}</p><p className="text-xs text-slate-500">Just now</p></div></div>)}</div></section>;
}
