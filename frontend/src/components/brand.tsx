import Image from "next/image";

type BrandProps = { className?: string; priority?: boolean };

export function BrandLogo({ className = "h-auto w-40", priority = false }: BrandProps) {
  return <Image src="/brand/sellora-logo.svg" alt="Sellora" width={640} height={180} priority={priority} className={className} />;
}

export function BrandIcon({ className = "h-10 w-10", priority = false }: BrandProps) {
  return <Image src="/brand/sellora-icon.svg" alt="Sellora icon" width={128} height={128} priority={priority} className={className} />;
}

export function BrandLockup({ className = "", markClassName = "h-10 w-10", textClassName = "text-white" }: { className?: string; markClassName?: string; textClassName?: string }) {
  return (
    <span className={`inline-flex min-w-0 items-center gap-3 ${className}`}>
      <span className="grid shrink-0 place-items-center rounded-2xl bg-white/5 p-1 ring-1 ring-white/10"><BrandIcon priority className={markClassName} /></span>
      <span className={`min-w-0 leading-tight ${textClassName}`}>
        <span className="block truncate text-lg font-black tracking-tight">Sellora</span>
        <span className="block truncate text-[11px] font-semibold uppercase tracking-[0.22em] opacity-65">Instagram CRM</span>
      </span>
    </span>
  );
}
