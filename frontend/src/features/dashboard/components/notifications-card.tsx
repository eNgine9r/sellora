export function NotificationsCard() {
  const items = ["3 замовлення очікують підтвердження", "2 товари нижче minimum stock", "1 shipment прибув у відділення"];
  return <section className="rounded-[20px] border border-slate-100 bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.06)]"><h2 className="text-lg font-black">Notifications</h2><div className="mt-4 grid gap-3">{items.map((item) => <div key={item} className="rounded-2xl bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">{item}</div>)}</div></section>;
}
