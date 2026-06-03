import Image from "next/image";

export function BrandLogo({ className = "h-auto w-40" }: { className?: string }) {
  return <Image src="/branding/sellora-logo.svg" alt="Sellora" width={640} height={180} priority className={className} />;
}

export function BrandIcon({ className = "h-10 w-10" }: { className?: string }) {
  return <Image src="/branding/sellora-icon.svg" alt="Sellora icon" width={128} height={128} className={className} />;
}
