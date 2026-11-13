"use client";

import { useEffect, useId, useRef, useState, type ChangeEvent, type MouseEvent } from "react";
import { useI18n } from "@/i18n/provider";

export const platformMfaCodeLength = 6;

function digits(value: string) {
  return value.replace(/[^0-9]/g, "").slice(0, platformMfaCodeLength);
}

export function PlatformMfaCode({ value, onChange, pending, error }: {
  value: string;
  onChange: (code: string) => void;
  pending: boolean;
  error?: string;
}) {
  const { t } = useI18n();
  const input = useRef<HTMLInputElement>(null);
  const id = useId();
  const [focused, setFocused] = useState(false);
  const [selection, setSelection] = useState({ start: 0, end: 0 });

  useEffect(() => {
    if (!pending) input.current?.focus({ preventScroll: true });
  }, [pending]);

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const field = event.currentTarget;
    const code = digits(field.value);
    const caret = digits(field.value.slice(0, field.selectionEnd ?? field.value.length)).length;
    if (field.value !== code) {
      field.value = code;
      field.setSelectionRange(caret, caret);
    }
    setSelection({ start: caret, end: caret });
    onChange(code);
  }

  function placeCaret(event: MouseEvent<HTMLInputElement>) {
    if (event.detail !== 1) return;
    const field = event.currentTarget;
    const bounds = field.getBoundingClientRect();
    const position = Math.round((event.clientX - bounds.left) / bounds.width * platformMfaCodeLength);
    const caret = Math.min(value.length, Math.max(0, position));
    field.setSelectionRange(caret, caret);
    setSelection({ start: caret, end: caret });
  }

  const active = Math.min(selection.end, value.length, platformMfaCodeLength - 1);

  return (
    <div className="grid gap-2.5">
      <label htmlFor={id} className="text-sm font-semibold text-text-primary">{t("platformAdmin.mfaCode")}</label>
      <div className="relative">
        <div aria-hidden="true" data-testid="platform-mfa-slots" className="grid grid-cols-6 gap-1.5 sm:gap-2.5">
          {Array.from({ length: platformMfaCodeLength }, (_, index) => {
            const selected = focused && index >= selection.start && index < selection.end;
            const current = focused && index === active;
            const tone = current || selected
              ? "border-violet-300 bg-violet-500/20 ring-2 ring-violet-400/30"
              : error
                ? "border-danger/50 bg-[var(--danger-surface)]"
                : value[index]
                  ? "border-violet-400/30 bg-violet-500/10"
                  : "border-border-strong bg-surface-2";
            return (
              <span key={index} className={`grid h-12 min-w-0 place-items-center rounded-xl border text-2xl font-semibold tabular-nums transition-colors sm:h-14 ${tone}`}>
                {value[index] || <span className={current ? "h-5 w-px rounded-full bg-violet-200" : "size-1 rounded-full bg-text-muted"} />}
              </span>
            );
          })}
        </div>
        <input
          ref={input}
          id={id}
          name="code"
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          autoCapitalize="none"
          spellCheck={false}
          pattern="[0-9]{6}"
          required
          disabled={pending}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-hint platform-mfa-error` : `${id}-hint`}
          value={value}
          onChange={handleChange}
          onClick={placeCaret}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onSelect={(event) => {
            const field = event.currentTarget;
            setSelection({ start: field.selectionStart ?? 0, end: field.selectionEnd ?? 0 });
          }}
          className="absolute inset-0 z-10 h-full w-full cursor-text text-base opacity-0 disabled:cursor-wait"
        />
      </div>
      <p id={`${id}-hint`} className="text-xs leading-5 text-text-secondary">
        {t("platformAdmin.mfaCodeHint")}
      </p>
    </div>
  );
}
