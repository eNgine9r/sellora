"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import { parseCodRegisterCsv } from "@/lib/cod-register-csv";
import { safeApiErrorMessage } from "@/services/api";
import { fetchCodLedger, importCodRegister, previewCodRegister } from "@/services/cod-reconciliation";
import type { CodImportRow, CodImportSource, CodPreview } from "@/types/cod-reconciliation";

const copy = {
  uk: {
    title: "Звірка виплат за ТТН", desc: "Реєстри NovaPay / виписки рахунку ФОП",
    confirmed: "Отримано за реєстрами", expected: "Історичні суми до звірки", review: "Потрібна перевірка",
    source: "Джерело", nova: "Реєстр NovaPay", bank: "Виписка банку",
    file: "Завантажити CSV", read: "Прочитати файл", preview: "Перевірити", import: "Імпортувати платежі",
    info: "CSV: ТТН, Сума (до комісії), Дата оплати. Додатково: Комісія, Номер платежу. Банківські рядки без ТТН потраплять на ручну перевірку.",
    confirm: "Я підтверджую, що файл містить фактично отримані платежі, а не створені ТТН.",
    duplicates: "Дублікати", matched: "Однозначні збіги", invalid: "На перевірку",
    noRows: "Платіжних записів ще немає", imported: "Нових платіжних записів:",
    guard: "Виплати відображаються окремо від доходу продажів. Звірка не змінює автоматично оплату, виручку, прибуток або склад.",
  },
  en: {
    title: "COD payment reconciliation", desc: "NovaPay registers / business bank statement",
    confirmed: "Confirmed register receipts", expected: "Historical amounts pending review", review: "Requires review",
    source: "Source", nova: "NovaPay register", bank: "Bank statement",
    file: "Upload CSV", read: "Read file", preview: "Preview matches", import: "Import payments",
    info: "CSV requires TTN, Amount (gross), Payment date. Optional: Fee, Transaction reference. Bank entries without TTN require manual review.",
    confirm: "I confirm the file contains actual payments, not created shipment requests.",
    duplicates: "Duplicates", matched: "Unique matches", invalid: "Review",
    noRows: "No payment records yet", imported: "New payment records:",
    guard: "Receipts are reported separately from sales. Reconciliation never automatically changes paid status, revenue, profit or inventory.",
  },
};

export function CodReconciliationSection() {
  const { locale } = useI18n();
  const t = locale === "en" ? copy.en : copy.uk;
  const { currentUser, currentWorkspace, currentWorkspaceId, status } = useAuth();
  const queryClient = useQueryClient();
  const currency = currentWorkspace?.currency_code ?? "UAH";
  const canEdit = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";
  const enabled = status === "authenticated" && Boolean(currentUser && currentWorkspaceId);
  const ledger = useQuery({ queryKey: ["cod-reconciliation", currentWorkspaceId], queryFn: () => fetchCodLedger(), enabled });
  const [source, setSource] = useState<CodImportSource>("NOVAPAY_REGISTER");
  const [file, setFile] = useState<File | null>(null);
  const [rows, setRows] = useState<CodImportRow[]>([]);
  const [preview, setPreview] = useState<CodPreview | null>(null);
  const [approved, setApproved] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const previewOp = useMutation({ mutationFn: previewCodRegister, onSuccess: setPreview });
  const importOp = useMutation({ mutationFn: importCodRegister, onSuccess: (result) => {
    setMessage(t.imported + " " + result.inserted_count);
    setRows([]); setPreview(null); setFile(null); setApproved(false);
    queryClient.invalidateQueries({ queryKey: ["cod-reconciliation", currentWorkspaceId] });
  } });

  async function readFile() {
    if (!file) return;
    setError(""); setMessage(""); setPreview(null); setApproved(false);
    try { setRows(parseCodRegisterCsv(await file.text(), source)); }
    catch (err) { setRows([]); setError(err instanceof Error ? err.message : "CSV error"); }
  }

  return <section id="cod-reconciliation" className="min-w-0 rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm sm:p-5" data-cod-reconciliation="v1">
    <h2 className="text-lg font-bold">{t.title}</h2>
    <p className="mt-1 text-sm text-text-secondary">{t.desc}</p>
    {ledger.isError ? <p role="alert" className="mt-2 text-sm text-danger">{safeApiErrorMessage(ledger.error)}</p> : null}
    {ledger.data ? <div className="mt-4 grid gap-2 sm:grid-cols-3">
      <div className="rounded-xl bg-surface-2 p-3"><p className="text-xs text-text-muted">{t.confirmed}</p><strong className="text-lg">{formatMoney(ledger.data.matched_receipts, currency)}</strong><p className="text-xs text-text-secondary">{ledger.data.matched_count}</p></div>
      <div className="rounded-xl bg-surface-2 p-3"><p className="text-xs text-text-muted">{t.expected}</p><strong className="text-lg">{formatMoney(ledger.data.pending_historical_amount, currency)}</strong><p className="text-xs text-text-secondary">{ledger.data.historical_amount_unverified_count}</p></div>
      <div className="rounded-xl bg-surface-2 p-3"><p className="text-xs text-text-muted">{t.review}</p><strong className="text-lg">{formatMoney(ledger.data.review_receipts, currency)}</strong><p className="text-xs text-text-secondary">{ledger.data.review_count}</p></div>
    </div> : null}
    {canEdit ? <div className="mt-4 grid gap-3 rounded-xl border border-border-subtle p-3">
      <label className="grid gap-1 text-sm font-medium">{t.source}<select value={source} onChange={e => { setSource(e.target.value as CodImportSource); setRows([]); setPreview(null); }} className="min-h-11 rounded-lg border border-input-border bg-input-background p-2"><option value="NOVAPAY_REGISTER">{t.nova}</option><option value="BANK_STATEMENT">{t.bank}</option></select></label>
      <label className="grid gap-1 text-sm font-medium">{t.file}<input type="file" accept=".csv,.txt,text/csv" className="min-h-11 min-w-0 w-full rounded-lg border border-input-border p-2" onChange={e => { setFile(e.target.files?.[0] ?? null); setRows([]); setPreview(null); setApproved(false); }} /></label>
      <p className="text-xs text-text-secondary">{t.info}</p>
      <div className="flex flex-wrap gap-2">
        <button type="button" disabled={!file || importOp.isPending} onClick={readFile} className="min-h-11 rounded-lg border border-border-subtle px-4 font-semibold disabled:opacity-40">{t.read}</button>
        <button type="button" disabled={!rows.length || previewOp.isPending || importOp.isPending} onClick={() => { setPreview(null); setApproved(false); previewOp.mutate(rows); }} className="min-h-11 rounded-lg bg-primary px-4 font-semibold text-primary-foreground disabled:opacity-40">{t.preview} ({rows.length})</button>
      </div>
      {error || previewOp.isError || importOp.isError ? <p role="alert" className="text-sm text-danger">{error || safeApiErrorMessage(previewOp.error || importOp.error)}</p> : null}
      {preview ? <div className="grid gap-3 rounded-xl bg-surface-2 p-3">
        <p className="text-sm font-semibold">{t.matched}: {preview.matched_count} · {t.invalid}: {preview.review_count} · {t.duplicates}: {preview.duplicate_count}</p>
        <div className="max-h-48 overflow-y-auto text-xs">{preview.rows.slice(0, 30).map((row, i) => <p key={row.reference + i} className="border-b border-border-subtle py-1">{row.tracking_number || "—"} · {row.status} {row.reason ? "· " + row.reason : ""}</p>)}</div>
        <label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={approved} onChange={e => setApproved(e.target.checked)} className="mt-1" />{t.confirm}</label>
        <button type="button" disabled={!approved || importOp.isPending} onClick={() => importOp.mutate(rows)} className="min-h-11 rounded-lg bg-primary px-4 font-semibold text-primary-foreground disabled:opacity-40">{t.import}</button>
      </div> : null}
      {message ? <p role="status" className="text-sm text-success">{message}</p> : null}
    </div> : null}
    <p className="mt-4 text-xs text-text-secondary">{t.guard}</p>
    {ledger.data?.rows.length ? <div className="mt-3 max-h-64 overflow-auto"><table className="min-w-full text-left text-xs"><thead><tr><th className="p-2">ТТН</th><th className="p-2">Дата</th><th className="p-2">Сума</th><th className="p-2">Статус</th></tr></thead><tbody>{ledger.data.rows.map(row => <tr key={row.id} className="border-t border-border-subtle"><td className="p-2">{row.tracking_number || "—"}</td><td className="p-2">{row.paid_at.slice(0,10)}</td><td className="p-2">{formatMoney(row.gross_amount, currency)}</td><td className="p-2">{row.status}</td></tr>)}</tbody></table></div> : <p className="mt-2 text-sm text-text-muted">{t.noRows}</p>}
  </section>;
}
