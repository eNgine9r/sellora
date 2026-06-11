"use client";

import { FormEvent, useState } from "react";
import { MessageSquare, X } from "lucide-react";
import { usePathname } from "next/navigation";
import { useI18n } from "@/i18n/provider";
import { FeedbackCategory, submitPilotFeedback } from "@/services/feedback";

const CATEGORIES: FeedbackCategory[] = ["ISSUE", "IDEA", "CONFUSION", "PRAISE", "OTHER"];

export function FeedbackDialog({ workspaceId }: { workspaceId: string | null }) {
  const { t } = useI18n();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState<FeedbackCategory>("ISSUE");
  const [rating, setRating] = useState("");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workspaceId || message.trim().length < 3) return;
    setStatus("submitting");
    try {
      await submitPilotFeedback(workspaceId, { category, rating: rating ? Number(rating) : null, message: message.trim(), page_path: pathname });
      setStatus("success");
      setMessage("");
      setRating("");
    } catch {
      setStatus("error");
    }
  }

  return (
    <>
      <button className="min-h-11 shrink-0 rounded-2xl border border-violet-200 bg-white px-3 text-sm font-black text-violet-700 shadow-sm transition hover:bg-violet-50 dark:border-violet-400/30 dark:bg-white/10 dark:text-violet-100" onClick={() => setOpen(true)} type="button">
        {t("feedback.button")}
      </button>
      {open ? (
        <div className="fixed inset-0 z-50 grid place-items-end bg-slate-950/45 p-0 sm:place-items-center sm:p-4" role="dialog" aria-modal="true" aria-label={t("feedback.form.title")}>
          <section className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-t-[28px] bg-white p-5 shadow-2xl dark:bg-slate-950 sm:rounded-[28px]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="inline-flex items-center gap-2 text-sm font-black uppercase tracking-[0.18em] text-violet-600"><MessageSquare className="h-4 w-4" />{t("feedback.button")}</p>
                <h2 className="mt-2 text-2xl font-black text-slate-950 dark:text-white">{t("feedback.form.title")}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{t("feedback.form.description")}</p>
              </div>
              <button className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-slate-100 text-slate-700 dark:bg-white/10 dark:text-white" onClick={() => setOpen(false)} type="button" aria-label={t("actions.cancel")}><X className="h-5 w-5" /></button>
            </div>
            <form className="mt-5 grid gap-4" onSubmit={onSubmit}>
              <label className="grid gap-2 text-sm font-bold text-slate-700 dark:text-slate-200">{t("feedback.form.category")}<select className="min-h-11 rounded-2xl border border-slate-200 bg-white px-3 text-slate-950 dark:border-white/10 dark:bg-white/10 dark:text-white" value={category} onChange={(event) => setCategory(event.target.value as FeedbackCategory)} required>{CATEGORIES.map((item) => <option key={item} value={item}>{t(`feedback.categories.${item}`)}</option>)}</select></label>
              <label className="grid gap-2 text-sm font-bold text-slate-700 dark:text-slate-200">{t("feedback.form.rating")}<select className="min-h-11 rounded-2xl border border-slate-200 bg-white px-3 text-slate-950 dark:border-white/10 dark:bg-white/10 dark:text-white" value={rating} onChange={(event) => setRating(event.target.value)}><option value="">{t("feedback.form.ratingOptional")}</option>{[1, 2, 3, 4, 5].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
              <label className="grid gap-2 text-sm font-bold text-slate-700 dark:text-slate-200">{t("feedback.form.message")}<textarea className="min-h-32 rounded-2xl border border-slate-200 bg-white p-3 text-slate-950 dark:border-white/10 dark:bg-white/10 dark:text-white" value={message} onChange={(event) => setMessage(event.target.value)} required minLength={3} maxLength={4000} placeholder={t("feedback.form.messagePlaceholder")} /></label>
              <p className="rounded-2xl bg-amber-50 p-3 text-sm font-semibold leading-6 text-amber-900 dark:bg-amber-400/10 dark:text-amber-100">{t("feedback.form.privacyHint")}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">{t("feedback.form.currentPage", { page: pathname })}</p>
              {status === "success" ? <p className="rounded-2xl bg-emerald-50 p-3 text-sm font-bold text-emerald-800 dark:bg-emerald-400/10 dark:text-emerald-100">{t("feedback.success.submitted")}</p> : null}
              {status === "error" ? <p className="rounded-2xl bg-rose-50 p-3 text-sm font-bold text-rose-800 dark:bg-rose-400/10 dark:text-rose-100">{t("feedback.errors.submitFailed")}</p> : null}
              <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                <button className="min-h-11 rounded-2xl border border-slate-200 px-4 text-sm font-black text-slate-700 dark:border-white/10 dark:text-slate-100" onClick={() => setOpen(false)} type="button">{t("actions.cancel")}</button>
                <button className="min-h-11 rounded-2xl bg-violet-700 px-4 text-sm font-black text-white disabled:cursor-not-allowed disabled:opacity-60" disabled={status === "submitting" || message.trim().length < 3 || !workspaceId} type="submit">{status === "submitting" ? t("feedback.form.submitting") : t("feedback.form.submit")}</button>
              </div>
            </form>
          </section>
        </div>
      ) : null}
    </>
  );
}
