"use client";

import { Bot, CheckCircle2, MessageCircle, Sparkles, X } from "lucide-react";
import { useState } from "react";
import { Button, WorkspaceHeader, WorkspacePage } from "@/components/crm-workspace";
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
  const [aiPanelOpen, setAiPanelOpen] = useState(false);

  return (
    <WorkspacePage className="min-h-full">
      <WorkspaceHeader
        eyebrow={t("direct.kicker")}
        title={t("direct.title")}
        description={t("direct.description")}
        actions={<Button>{t("direct.createSynthetic")}</Button>}
      />

      <div className="lg:hidden">
        <button type="button" onClick={() => setAiPanelOpen(true)} className="min-h-11 w-full rounded-2xl border border-border-subtle bg-surface-1 px-4 py-2 text-sm font-black text-primary shadow-[var(--shadow-card)]">
          {t("direct.openAiPanel")}
        </button>
      </div>

      <section className="grid min-h-[calc(100dvh-var(--topbar-height,72px)-190px)] min-w-0 gap-4 lg:grid-cols-[minmax(260px,320px)_minmax(0,1fr)_minmax(320px,380px)]" data-direct-shell-content>
        <ConversationList t={t} />
        <MessageThread t={t} />
        <div className="hidden lg:block"><AiPanel t={t} /></div>
      </section>

      {aiPanelOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label={t("direct.aiPanel")}> 
          <button type="button" className="absolute inset-0 bg-[var(--overlay-background)] backdrop-blur-sm" aria-label={t("actions.close")} onClick={() => setAiPanelOpen(false)} />
          <aside className="absolute inset-y-0 right-0 flex w-[92vw] max-w-md flex-col overflow-hidden bg-surface-1 shadow-2xl">
            <header className="flex items-center justify-between border-b border-border-subtle p-4">
              <div className="flex items-center gap-2"><Bot className="h-5 w-5 text-primary" /><h2 className="font-black">{t("direct.aiPanel")}</h2></div>
              <button type="button" className="rounded-2xl p-2 text-text-secondary hover:bg-surface-hover" onClick={() => setAiPanelOpen(false)} aria-label={t("actions.close")}><X className="h-5 w-5" /></button>
            </header>
            <div className="sellora-scrollbar min-h-0 flex-1 overflow-y-auto p-4"><AiPanel t={t} embedded /></div>
          </aside>
        </div>
      ) : null}
    </WorkspacePage>
  );
}

function ConversationList({ t }: { t: (key: string) => string }) {
  return <aside className="min-w-0 rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-3 shadow-[var(--shadow-card)]">
    <div className="mb-3 flex items-center justify-between"><h2 className="font-black">{t("direct.conversations")}</h2><span className="rounded-full bg-primary/15 px-2 py-1 text-xs font-bold text-primary">{t("direct.syntheticBadge")}</span></div>
    <input className="mb-3 min-h-11 w-full rounded-2xl border border-border-subtle bg-surface-2 px-3 text-sm" placeholder={t("direct.search")} />
    <div className="flex flex-wrap gap-2 pb-3 text-xs font-bold text-text-secondary"><span>Open</span><span>Urgent</span><span>Synthetic</span><span>Spam</span></div>
    <div className="space-y-2">{conversations.map((item) => <article key={item.username} className="rounded-2xl border border-border-subtle bg-surface-2 p-3"><div className="flex items-start justify-between gap-2"><div><h3 className="font-black">{item.name}</h3><p className="text-xs text-text-muted">{item.username}</p></div>{item.unread ? <span className="rounded-full bg-rose-500 px-2 py-0.5 text-xs font-black text-white">{item.unread}</span> : null}</div><p className="mt-2 line-clamp-2 text-sm text-text-secondary">{item.message}</p><div className="mt-3 flex flex-wrap gap-2"><span className="rounded-full bg-violet-500/15 px-2 py-1 text-xs font-bold text-primary">{item.intent}</span><span className="rounded-full bg-emerald-500/15 px-2 py-1 text-xs font-bold text-emerald-600">{item.status}</span></div></article>)}</div>
  </aside>;
}

function MessageThread({ t }: { t: (key: string) => string }) {
  return <section className="flex min-h-[520px] min-w-0 flex-col rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 shadow-[var(--shadow-card)]">
    <header className="border-b border-border-subtle p-4"><h2 className="font-black">Олена <span className="text-sm font-bold text-text-muted">@olena.shop</span></h2><p className="text-sm text-text-secondary">{t("direct.syntheticBadge")} · linked customer/order ще не обрано</p></header>
    <div className="sellora-scrollbar flex-1 space-y-3 overflow-y-auto p-4">{messages.map((m) => <div key={m.text} className={`flex ${m.align === "right" ? "justify-end" : "justify-start"}`}><div className={`max-w-[82%] rounded-3xl px-4 py-3 text-sm ${m.align === "right" ? "bg-primary/15 text-text-primary" : "bg-surface-2"}`}><p className="mb-1 text-xs font-black text-text-muted">{m.author}</p>{m.text}</div></div>)}</div>
    <footer className="border-t border-border-subtle p-3"><div className="rounded-2xl border border-dashed border-border-subtle p-3 text-sm text-text-muted">{t("direct.noAutoSend")}</div></footer>
  </section>;
}

function AiPanel({ t, embedded = false }: { t: (key: string) => string; embedded?: boolean }) {
  return <aside className={`${embedded ? "" : "h-full"} min-w-0 rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-4 shadow-[var(--shadow-card)]`} data-direct-ai-panel>
    {!embedded ? <div className="mb-4 flex items-center gap-2"><Bot className="h-5 w-5 text-primary" /><h2 className="font-black">{t("direct.aiPanel")}</h2></div> : null}
    <div className="space-y-3 text-sm">
      <Card icon={<Sparkles />} title="Короткий підсумок" body="Клієнт хоче замовити чорний годинник і питає про післяплату." />
      <Card icon={<MessageCircle />} title="Намір клієнта" body="Хоче оформити замовлення · Висока впевненість (94%)" />
      <Card title="Виявлені дані" body="Товар: чорний годинник · Оплата: COD — накладений платіж · Відсутні: телефон, відділення" />
      <Card title="CRM-дії" body="AI може підготувати лише чернетку ліда, клієнта або замовлення. Менеджер підтверджує дію вручну." />
    </div>
    <div className="sticky bottom-0 mt-4 grid gap-2 bg-surface-1 pt-3 sm:grid-cols-2"><button className="min-h-11 rounded-2xl bg-primary px-3 py-2 text-sm font-black text-white">Застосувати</button><button className="min-h-11 rounded-2xl border border-border-subtle px-3 py-2 text-sm font-black">Відхилити</button><button className="min-h-11 rounded-2xl border border-border-subtle px-3 py-2 text-sm font-black">Редагувати</button><button className="min-h-11 rounded-2xl border border-border-subtle px-3 py-2 text-sm font-black">Попросити уточнення</button></div>
  </aside>;
}

function Card({ title, body, icon }: { title: string; body: string; icon?: React.ReactNode }) {
  return <section className="rounded-2xl border border-border-subtle bg-surface-2 p-3"><div className="mb-1 flex items-center gap-2 font-black">{icon ? <span className="h-4 w-4 text-primary">{icon}</span> : <CheckCircle2 className="h-4 w-4 text-emerald-500" />}{title}</div><p className="text-text-secondary">{body}</p></section>;
}
