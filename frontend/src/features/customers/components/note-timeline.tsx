import { CustomerNote } from "@/types/crm-completion";
import { useI18n } from "@/i18n/provider";

export function NoteTimeline({ notes }: { notes: CustomerNote[] }) {
  const { t } = useI18n();
  return <div className="grid gap-3">{notes.map((note) => <div key={note.id} className="border-l-2 border-blue-500 pl-3"><p className="text-sm text-slate-900">{note.note}</p><p className="text-xs text-slate-500">{new Date(note.created_at).toLocaleString()}</p></div>)}{notes.length === 0 ? <p className="text-sm text-slate-500">{t("customers.noNotes")}</p> : null}</div>;
}
