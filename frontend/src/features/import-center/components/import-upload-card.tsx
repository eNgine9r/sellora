"use client";

import { ChangeEvent, useRef, useState } from "react";
import { useI18n } from "@/i18n/provider";

export function ImportUploadCard({ onUpload }: { onUpload: (file: File) => void }) {
  const { t } = useI18n();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [fileName, setFileName] = useState(t("importCenter.noFile"));

  function handleFile(event: ChangeEvent<HTMLInputElement>) { const file = event.target.files?.[0]; if (!file) return; setFileName(file.name); onUpload(file); }

  return (
    <section className="sellora-card w-full min-w-0 max-w-full overflow-hidden rounded-xl bg-white p-4 shadow-sm">
      <h2 className="font-semibold">{t("importCenter.uploadExcel")}</h2>
      <div className="mt-3 grid w-full min-w-0 max-w-full gap-2 sm:grid-cols-[auto_minmax(0,1fr)] sm:items-center">
        <input ref={inputRef} className="sr-only" type="file" accept=".xlsx,.csv" onChange={handleFile} />
        <button className="min-h-11 w-full min-w-0 max-w-full rounded-xl bg-blue-600 px-4 py-2 font-bold text-white sm:w-auto" type="button" onClick={() => inputRef.current?.click()}>{t("importCenter.chooseFile")}</button>
        <p className="min-w-0 truncate rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-600 dark:bg-white/[0.05] dark:text-slate-300" title={fileName}>{fileName}</p>
      </div>
      <p className="mt-2 break-words text-sm text-slate-500">{t("importCenter.subtitle")}</p>
    </section>
  );
}
