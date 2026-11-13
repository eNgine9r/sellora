"use client";

import { LoaderCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { useI18n } from "@/i18n/provider";
import { PublicAuthError, type SignInProvider } from "@/services/auth.service";
import styles from "./login.module.css";

const AUTH_ERRORS = [
  "expired", "cancelled", "provider_error", "account_required", "account_exists", "provider_in_use",
  "session_required", "verified_email_required", "invalid_code", "delivery_failed", "invalid_request",
  "invalid_registration", "unavailable", "registration_unavailable",
];

export function publicAuthErrorKey(error: unknown) {
  const code = error instanceof PublicAuthError ? error.code : error;
  return typeof code === "string" && AUTH_ERRORS.includes(code) ? `auth.access.errors.${code}` : "auth.networkError";
}

export function useAuthResult() {
  const [result, setResult] = useState<string | null>(null);
  useEffect(() => {
    setResult(new URLSearchParams(window.location.search).get("auth"));
  }, []);
  return result;
}

export function ProviderIcon({ provider }: { provider: SignInProvider }) {
  if (provider === "facebook") {
    return (
      <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="12" fill="#0866ff" />
        <path fill="#fff" d="M13.85 24v-8.76h2.96l.44-3.43h-3.4V9.62c0-.99.28-1.67 1.7-1.67h1.81V4.89a24 24 0 0 0-2.63-.14c-2.6 0-4.37 1.58-4.37 4.49v2.57H7.43v3.43h2.93V24z" />
      </svg>
    );
  }
  return (
    <svg width="20" height="20" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#4285F4" d="M43.6 24.5c0-1.4-.1-2.7-.4-4H24v7.6h11c-.5 2.5-1.9 4.6-4.1 6.1l6.6 5.1c3.9-3.6 6.1-8.8 6.1-14.8z" />
      <path fill="#34A853" d="M24 44c5.5 0 10.2-1.8 13.5-4.8L31 34.1c-1.8 1.2-4.2 2-7 2-5.3 0-9.7-3.6-11.3-8.4l-6.8 5.3A20 20 0 0 0 24 44z" />
      <path fill="#FBBC05" d="M12.7 27.7a12 12 0 0 1 0-7.4l-6.8-5.3a20 20 0 0 0 0 18z" />
      <path fill="#EA4335" d="M24 11.9c3 0 5.6 1 7.7 3l5.8-5.8A19.2 19.2 0 0 0 24 4 20 20 0 0 0 5.9 15l6.8 5.3C14.3 15.5 18.7 12 24 12z" />
    </svg>
  );
}

export function ProviderButtons({ providers, pending, disabled, onChoose }: {
  providers: SignInProvider[];
  pending: SignInProvider | null;
  disabled?: boolean;
  onChoose: (provider: SignInProvider) => void;
}) {
  const { t } = useI18n();
  return (
    <div className={styles.providerList}>
      {providers.map(provider => (
        <button key={provider} className={styles.providerButton} type="button"
          disabled={disabled || pending !== null} aria-busy={pending === provider} onClick={() => onChoose(provider)}>
          <ProviderIcon provider={provider} />
          {t(`auth.access.continue.${provider}`)}
          {pending === provider ? <LoaderCircle className="animate-spin motion-reduce:animate-none" size={17} aria-hidden="true" /> : <span />}
        </button>
      ))}
    </div>
  );
}
