export function NotificationsCard() {
  const items = ["3 замовлення очікують підтвердження", "2 товари нижче minimum stock", "1 shipment прибув у відділення"];
  return <section className="min-w-0 rounded-[20px] border border-slate-100 bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.06)] dark:border-white/10 dark:bg-slate-900 dark:shadow-none"><h2 className="text-lg font-black text-slate-950 dark:text-white">Notifications</h2><div className="mt-4 grid min-w-0 gap-3">{items.map((item) => <div key={item} className="min-w-0 rounded-2xl bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800 dark:bg-amber-400/15 dark:text-amber-100">{item}</div>)}</div></section>;
}
