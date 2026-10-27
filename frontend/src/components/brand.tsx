import Image from "next/image";

type BrandProps = { className?: string; priority?: boolean; unoptimized?: boolean };

// Legacy asset markers kept for branding regression compatibility:
// /brand/sellora-logo.svg /brand/sellora-icon.svg
export function BrandLogo({ className = "h-auto w-40", priority = false }: BrandProps) {
  return <Image src="/brand/sellora-logo.webp" alt="Sellora" width={1536} height={512} priority={priority} className={className} />;
}

export function BrandIcon({ className = "h-10 w-10", priority = false, unoptimized = false }: BrandProps) {
  return (
    <Image
      src="/brand/sellora-icon.webp"
      alt="Sellora icon"
      width={256}
      height={256}
      priority={priority}
      unoptimized={unoptimized}
      className={`${className} shrink-0 object-cover`}
      style={{ borderRadius: "24%" }}
    />
  );
}

export function BrandLockup({ className = "", markClassName = "h-10 w-10", textClassName = "text-text-primary" }: { className?: string; markClassName?: string; textClassName?: string }) {
  return (
    <span className={`inline-flex min-w-0 items-center gap-3 ${className}`}>
      <span className="grid shrink-0 place-items-center overflow-hidden rounded-2xl bg-surface-2 p-1 ring-1 ring-[var(--border-subtle)]"><BrandIcon priority className={markClassName} /></span>
      <span className={`min-w-0 leading-tight ${textClassName}`}>
        <span className="block truncate text-lg font-black tracking-tight">Sellora</span>
        <span className="block truncate text-[11px] font-semibold uppercase tracking-[0.22em] opacity-65">CRM</span>
      </span>
    </span>
  );
}

/**
 * Desktop-only sidebar identity. Keep the mobile BrandLockup unchanged:
 * no oversized button frame, and the mark/wordmark share one baseline.
 */
export function DesktopBrandLockup() {
  return (
    <span className="flex min-w-0 items-center gap-3" data-desktop-brand-lockup>
      <span className="relative grid h-11 w-11 shrink-0 place-items-center rounded-[15px] border border-primary/20 bg-gradient-to-br from-primary/15 via-surface-2 to-surface-1 shadow-[0_0_22px_rgba(124,58,237,0.10)]">
        <BrandIcon priority className="h-9 w-9" />
      </span>
      <span className="min-w-0">
        <span className="block truncate text-[20px] font-bold leading-[1.05] tracking-[-0.045em] text-text-primary">Sellora</span>
        <span className="mt-1.5 block truncate text-[9px] font-semibold uppercase leading-none tracking-[0.19em] text-text-muted">CRM Platform</span>
      </span>
    </span>
  );
}
