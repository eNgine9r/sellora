"use client";

import { useI18n } from "@/i18n/provider";
import { ImportLog } from "@/types/import-center";
export function ImportLogsTable({ logs }: { logs: ImportLog[] }) { const { t } = useI18n(); return <div className="w-full min-w-0 max-w-full overflow-hidden rounded-xl bg-white p-4 shadow-sm"><h2 className="mb-3 font-semibold">{t("importCenter.logs")}</h2><div className="sellora-scrollbar max-w-full overflow-x-auto"><table className="w-full min-w-[640px] text-left text-sm"><thead><tr className="text-slate-500"><th>{t("tables.row")}</th><th>{t("tables.status")}</th><th>{t("tables.message")}</th></tr></thead><tbody>{logs.map((log) => <tr className="border-t" key={log.id}><td className="py-2">{log.row_number}</td><td>{log.status}</td><td>{log.message}</td></tr>)}</tbody></table></div></div>; }
