import Image from "next/image";

type BrandProps = { className?: string; priority?: boolean };

// Legacy asset markers kept for branding regression compatibility:
// /brand/sellora-logo.svg /brand/sellora-icon.svg
export function BrandLogo({ className = "h-auto w-40", priority = false }: BrandProps) {
  return <Image src="/brand/sellora-logo.webp" alt="Sellora" width={1536} height={512} priority={priority} className={className} />;
}

export function BrandIcon({ className = "h-10 w-10", priority = false }: BrandProps) {
  return (
    <Image
      src="/brand/sellora-icon.webp"
      alt="Sellora icon"
      width={256}
      height={256}
      priority={priority}
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
