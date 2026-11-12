import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Platform Admin | Sellora",
  robots: { index: false, follow: false },
};

export default function PlatformAdminLayout({ children }: { children: ReactNode }) {
  return <div className="dark min-h-dvh bg-canvas text-text-primary">{children}</div>;
}
