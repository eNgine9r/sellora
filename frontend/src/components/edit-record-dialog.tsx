"use client";

import { FormEvent, useState } from "react";
import { Modal } from "@/components/ui/overlay";
import { Button, FormField, Input, Select, Textarea } from "@/components/ui/primitives";
import { useI18n } from "@/i18n/provider";

type EditField = { name: string; label: string; type?: "text" | "number" | "date" | "select" | "textarea"; options?: { value: string; label: string }[] };

export function EditRecordDialog({ title, fields, initialValues, isSubmitting = false, submitError, onClose, onSubmit }: { title: string; fields: EditField[]; initialValues: object; isSubmitting?: boolean; submitError?: string | null; onClose: () => void; onSubmit: (values: Record<string, string>) => void }) {
  const { t } = useI18n();
  const [values, setValues] = useState<Record<string, string>>(() => Object.fromEntries(fields.map((field) => [field.name, (initialValues as Record<string, unknown>)[field.name] == null ? "" : String((initialValues as Record<string, unknown>)[field.name])])));
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); onSubmit(values); }

  return (
    <Modal open title={title} onClose={onClose} size="lg">
      <form className="grid min-w-0 gap-4 overflow-x-hidden" onSubmit={submit} noValidate>
        {fields.map((field) => (
          <FormField label={field.label} key={field.name}>
            {field.type === "textarea" ? (
              <Textarea value={values[field.name] ?? ""} onChange={(event) => setValues({ ...values, [field.name]: event.target.value })} />
            ) : field.type === "select" ? (
              <Select value={values[field.name] ?? ""} onChange={(event) => setValues({ ...values, [field.name]: event.target.value })}>
                {field.options?.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </Select>
            ) : (
              <Input inputMode={field.type === "number" ? "decimal" : undefined} type={field.type === "date" ? "date" : "text"} value={values[field.name] ?? ""} onChange={(event) => setValues({ ...values, [field.name]: event.target.value })} />
            )}
          </FormField>
        ))}
        {submitError ? <p className="rounded-2xl border border-danger/25 bg-[var(--danger-surface)] px-3 py-2 text-sm font-bold text-[var(--danger-foreground)]">{submitError}</p> : null}
        <div className="grid gap-3 sm:grid-cols-2">
          <Button variant="secondary" disabled={isSubmitting} onClick={onClose} type="button">{t("actions.cancel")}</Button>
          <Button loading={isSubmitting} type="submit">{t("actions.saveChanges")}</Button>
        </div>
      </form>
    </Modal>
  );
}
