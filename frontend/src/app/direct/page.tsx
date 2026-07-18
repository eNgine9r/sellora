"use client";

import { Bot, CheckCircle2, MessageCircle, Sparkles } from "lucide-react";
import { useI18n } from "@/i18n/provider";

const conversations = [
  { name: "Олена", username: "@olena.shop", intent: "Хоче оформити замовлення", status: "Тестовий діалог", unread: 2, message: "Хочу чорний годинник післяплатою" },
  { name: "Ірина", username: "@ira_style", intent: "Питання про доставку", status: "Очікує менеджера", unread: 1, message: "Коли зможете відправити у Луцьк?" },
  { name: "Spam", username: "@promo_fast", intent: "Spam", status: "Низький пріоритет", unread: 0, message: "🔥🔥🔥 просування акаунтів" },
];

const messages = [
  { author: "Клієнт", text: "Добрий день, хочу чорний годинник, можна післяплатою?", align: "left" },
  { author: "Sellora", text: "Чернетка AI — не відправлено: Уточніть, будь ласка, номер телефону та відділення Нової пошти.", align: "right" },
];

export default function DirectPage() {
  const { t } = useI18n();
  return (
    <main className="min-h-screen bg-bg px-3 py-4 text-text-primary sm:px-5 lg:px-6">
      <div className="mb-4 flex flex-col gap-3 rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-4 shadow-[var(--shadow-card)] md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.24em] text-primary">{t("direct.kicker")}</p>
          <h1 className="mt-1 text-2xl font-black tracking-tight md:text-3xl">{t("direct.title")}</h1>
          <p className="mt-2 max-w-3xl text-sm text-text-secondary">{t("direct.description")}</p>
        </div>
        <button className="min-h-11 rounded-2xl bg-primary px-4 py-2 text-sm font-black text-white shadow-[var(--shadow-card)]">{t("direct.createSynthetic")}</button>
      </div>

      <section className="grid min-h-[72vh] gap-4 lg:grid-cols-[320px_minmax(0,1fr)_380px]">
        <aside className="rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-3 shadow-[var(--shadow-card)]">
          <div className="mb-3 flex items-center justify-between"><h2 className="font-black">{t("direct.conversations")}</h2><span className="rounded-full bg-primary/15 px-2 py-1 text-xs font-bold text-primary">Synthetic</span></div>
          <input className="mb-3 min-h-11 w-full rounded-2xl border border-border-subtle bg-surface-2 px-3 text-sm" placeholder={t("direct.search")} />
          <div className="flex flex-wrap gap-2 pb-3 text-xs font-bold text-text-secondary"><span>Open</span><span>Urgent</span><span>Synthetic</span><span>Spam</span></div>
          <div className="space-y-2">
            {conversations.map((item) => <article key={item.username} className="rounded-2xl border border-border-subtle bg-surface-2 p-3"><div className="flex items-start justify-between gap-2"><div><h3 className="font-black">{item.name}</h3><p className="text-xs text-text-muted">{item.username}</p></div>{item.unread ? <span className="rounded-full bg-rose-500 px-2 py-0.5 text-xs font-black text-white">{item.unread}</span> : null}</div><p className="mt-2 line-clamp-2 text-sm text-text-secondary">{item.message}</p><div className="mt-3 flex flex-wrap gap-2"><span className="rounded-full bg-violet-500/15 px-2 py-1 text-xs font-bold text-primary">{item.intent}</span><span className="rounded-full bg-emerald-500/15 px-2 py-1 text-xs font-bold text-emerald-600">{item.status}</span></div></article>)}
          </div>
        </aside>

        <section className="flex min-h-[560px] flex-col rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 shadow-[var(--shadow-card)]">
          <header className="border-b border-border-subtle p-4"><h2 className="font-black">Олена <span className="text-sm font-bold text-text-muted">@olena.shop</span></h2><p className="text-sm text-text-secondary">Тестовий діалог · linked customer/order ще не обрано</p></header>
          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {messages.map((m) => <div key={m.text} className={`flex ${m.align === "right" ? "justify-end" : "justify-start"}`}><div className={`max-w-[82%] rounded-3xl px-4 py-3 text-sm ${m.align === "right" ? "bg-primary/15 text-text-primary" : "bg-surface-2"}`}><p className="mb-1 text-xs font-black text-text-muted">{m.author}</p>{m.text}</div></div>)}
          </div>
          <footer className="border-t border-border-subtle p-3"><div className="rounded-2xl border border-dashed border-border-subtle p-3 text-sm text-text-muted">{t("direct.noAutoSend")}</div></footer>
        </section>

        <aside className="rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-4 shadow-[var(--shadow-card)]">
          <div className="mb-4 flex items-center gap-2"><Bot className="h-5 w-5 text-primary" /><h2 className="font-black">{t("direct.aiPanel")}</h2></div>
          <div className="space-y-3 text-sm">
            <Card icon={<Sparkles />} title="Короткий підсумок" body="Клієнт хоче замовити чорний годинник і питає про післяплату." />
            <Card icon={<MessageCircle />} title="Намір клієнта" body="Хоче оформити замовлення · Висока впевненість (94%)" />
            <Card title="Виявлені дані" body="Товар: чорний годинник · Оплата: COD — накладений платіж · Відсутні: телефон, відділення" />
            <Card title="CRM-дії" body="AI може підготувати лише чернетку ліда, клієнта або замовлення. Менеджер підтверджує дію вручну." />
          </div>
          <div className="sticky bottom-0 mt-4 grid gap-2 bg-surface-1 pt-3 sm:grid-cols-2"><button className="min-h-11 rounded-2xl bg-primary px-3 py-2 text-sm font-black text-white">Застосувати</button><button className="min-h-11 rounded-2xl border border-border-subtle px-3 py-2 text-sm font-black">Відхилити</button><button className="min-h-11 rounded-2xl border border-border-subtle px-3 py-2 text-sm font-black">Редагувати</button><button className="min-h-11 rounded-2xl border border-border-subtle px-3 py-2 text-sm font-black">Попросити уточнення</button></div>
        </aside>
      </section>
    </main>
  );
}

function Card({ title, body, icon }: { title: string; body: string; icon?: React.ReactNode }) {
  return <section className="rounded-2xl border border-border-subtle bg-surface-2 p-3"><div className="mb-1 flex items-center gap-2 font-black">{icon ? <span className="h-4 w-4 text-primary">{icon}</span> : <CheckCircle2 className="h-4 w-4 text-emerald-500" />}{title}</div><p className="text-text-secondary">{body}</p></section>;
}
