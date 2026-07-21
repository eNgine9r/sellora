"use client";

import { ChangeEvent, type ReactNode } from "react";
import { Button, FilterBar as SharedFilterBar, Input, Select } from "@/components/ui/primitives";
import { useI18n } from "@/i18n/provider";

type Option = { value: string; label: string };

export function FilterBar({ children }: { children: ReactNode }) {
  return <SharedFilterBar>{children}</SharedFilterBar>;
}

export function SearchInput({ value, onChange, placeholder, ariaLabel }: { value: string; onChange: (value: string) => void; placeholder: string; ariaLabel?: string }) {
  return <Input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} aria-label={ariaLabel ?? placeholder} />;
}

export function SortSelect({ value, onChange, options, label }: { value: string; onChange: (value: string) => void; options: Option[]; label?: string }) {
  const { t } = useI18n();
  return <Select value={value} onChange={(event: ChangeEvent<HTMLSelectElement>) => onChange(event.target.value)} aria-label={label ?? t("filters.sort")}>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</Select>;
}

export function ResetFiltersButton({ onClick }: { onClick: () => void }) {
  const { t } = useI18n();
  return <Button variant="secondary" type="button" onClick={onClick}>{t("filters.reset")}</Button>;
}
