"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { parseBankEvidenceCsv, type BankImportRow } from "@/lib/bank-payment-evidence-csv";
import { safeApiErrorMessage } from "@/services/api";
import { importBankEvidence, previewBankEvidence } from "@/services/bank-payment-evidence";
import type { BankEvidencePreview } from "@/types/bank-payment-evidence";

const labels = {
  uk: {
    title: "Імпорт даних для ручної перевірки",
    help: "Необов'язковий імпорт підготовленого CSV, поки офіційне банківське підключення не активне.",
    caution: "Цей файл не є банківським підтвердженням. Імпорт не переводить замовлення в «Оплачено» і не змінює прибуток.",
    template: "Завантажити шаблон CSV",
    columns: "Стовпці: ID рахунку, унікальний ID операції, спосіб, тип платежу, сума в гривнях, точна дата/час з часовим поясом.",
    choose: "Вибрати CSV", check: "Перевірити файл", preview: "Попередній перегляд",
    candidates: "Кандидати", review: "На перевірці", duplicates: "Дублікати",
    confirm: "Я підтверджую, що це перевірені мною дані та хочу зберегти їх лише як записи для звіряння.",
    import: "Зберегти записи для звіряння", saved: "Нових записів збережено:",
    noFile: "Оберіть файл із шаблоном Sellora", noBank: "Банківський токен чи квитанцію з персональними даними сюди не завантажуйте.",
  },
  en: {
    title: "Import evidence for manual review",
    help: "Optional prepared CSV import while the authorized bank connection is not active.",
    caution: "Imported data is not a bank confirmation. Import never marks an order paid or changes profit.",
    template: "Download CSV template",
    columns: "Columns: account ID, unique transaction ID, method, payment kind, UAH amount, timezone-aware date/time.",
    choose: "Choose CSV", check: "Validate file", preview: "Preview",
    candidates: "Candidates", review: "Review", duplicates: "Duplicates",
    confirm: "I confirm that I reviewed these records and want to store them only as reconciliation evidence.",
    import: "Store records for review", saved: "New evidence records saved:",
    noFile: "Choose a file using the Sellora template", noBank: "Do not upload bank access tokens or identity documents.",
  },
};

export function MonobankEvidenceImport() {
  const { locale } = useI18n();
  const t = locale === "en" ? labels.en : labels.uk;
  const { currentWorkspace, currentWorkspaceId } = useAuth();
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [rows, setRows] = useState<BankImportRow[]>([]);
  const [preview, setPreview] = useState<BankEvidencePreview | null>(null);
  const [approved, setApproved] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const previewOp = useMutation({ mutationFn: previewBankEvidence, onSuccess: setPreview });
  const importOp = useMutation({
    mutationFn: importBankEvidence,
    onSuccess: async result => {
      setSuccess(t.saved + " " + result.inserted_count);
      setFile(null); setRows([]); setPreview(null); setApproved(false);
      await queryClient.invalidateQueries({ queryKey: ["monobank-evidence", currentWorkspaceId] });
    },
  });

  if (currentWorkspace?.role !== "OWNER") return null;

  async function validateFile() {
    if (!file) return;
    setRows([]); setPreview(null); setApproved(false); setError(""); setSuccess("");
    try {
      if (file.size > 1_000_000) throw new Error("File too large (max 1 MB)");
      const result = parseBankEvidenceCsv(await file.text());
      setRows(result);
    } catch (err) {
      // CSV values are never reflected in validation errors.
      setError(err instanceof Error ? err.message : t.noFile);
    }
  }

  return <div className="mt-4 rounded-xl border border-border-subtle bg-surface-2 p-3" data-bank-evidence-import="review-only-v2">
    <h3 className="font-semibold">{t.title}</h3>
    <p className="mt-1 text-sm text-text-secondary">{t.help}</p>
    <p className="mt-2 text-xs font-medium text-text-secondary">{t.caution}</p>
    <div className="mt-3 flex flex-wrap items-center gap-3">
      <a href="/templates/monobank-evidence-template.txt" download="monobank-evidence.csv" className="text-sm font-semibold text-primary underline underline-offset-2">{t.template}</a>
    </div>
    <p className="mt-2 text-xs text-text-muted">{t.columns}</p>
    <p className="mt-1 text-xs text-text-muted">{t.noBank}</p>
    <div className="mt-3 flex flex-wrap items-end gap-2">
      <label className="grid min-w-0 flex-1 gap-1 text-xs font-medium">{t.choose}
        <input type="file" accept=".csv,text/csv" className="min-h-11 w-full min-w-0 rounded-lg border border-input-border bg-input-background px-2 py-2"
          onChange={e => { setFile(e.target.files?.[0] ?? null); setRows([]); setPreview(null); setApproved(false); setError(""); setSuccess(""); }} />
      </label>
      <button type="button" disabled={!file || previewOp.isPending || importOp.isPending} onClick={validateFile} className="min-h-11 rounded-lg border border-border-subtle bg-surface-1 px-3 font-semibold disabled:opacity-40">{t.check}</button>
      <button type="button" disabled={!rows.length || previewOp.isPending || importOp.isPending} onClick={() => { setPreview(null); setApproved(false); previewOp.mutate(rows); }} className="min-h-11 rounded-lg bg-primary px-4 font-semibold text-primary-foreground disabled:opacity-40">{t.preview} ({rows.length})</button>
    </div>
    {error || previewOp.isError || importOp.isError ? <p role="alert" className="mt-3 text-sm text-danger">{error || safeApiErrorMessage(previewOp.error || importOp.error)}</p> : null}
    {preview ? <div className="mt-4 rounded-lg border border-border-subtle bg-surface-1 p-3">
      <p className="text-sm font-semibold">{t.candidates}: {preview.candidate_count} · {t.review}: {preview.review_count} · {t.duplicates}: {preview.duplicate_count}</p>
      <div className="mt-2 max-h-32 overflow-auto text-xs text-text-secondary">
        {preview.rows.slice(0, 30).map((item, i) => <p key={item.external_reference + i} className="border-b border-border-subtle py-1">{item.rail} · {item.reason}</p>)}
      </div>
      <label className="mt-3 flex items-start gap-2 text-sm">
        <input type="checkbox" checked={approved} onChange={e => setApproved(e.target.checked)} className="mt-1" />
        {t.confirm}
      </label>
      <button type="button" disabled={!approved || importOp.isPending || previewOp.isPending} onClick={() => importOp.mutate(rows)} className="mt-3 min-h-11 rounded-lg bg-primary px-4 font-semibold text-primary-foreground disabled:opacity-40">{t.import}</button>
    </div> : null}
    {success ? <p role="status" className="mt-3 text-sm text-success">{success}</p> : null}
  </div>;
}
