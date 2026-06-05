import type { Metadata, Viewport } from "next";
import { AppShell } from "@/components/app-shell";
import { QueryProvider } from "@/providers/query-provider";
import { AuthProvider } from "@/stores/auth.store";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sellora CRM",
  description: "Premium CRM for Instagram stores",
  applicationName: "Sellora",
  manifest: "/manifest.webmanifest",
  appleWebApp: { capable: true, title: "Sellora", statusBarStyle: "black-translucent" },
  icons: {
    icon: [{ url: "/brand/sellora-icon.svg", type: "image/svg+xml" }],
    apple: [{ url: "/brand/sellora-icon.svg", type: "image/svg+xml" }],
  },
};

export const viewport: Viewport = {
  themeColor: "#080812",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="overflow-x-hidden bg-[#080812]">
      <body className="min-w-0 overflow-x-hidden bg-[#F8F7FC] antialiased">
        <QueryProvider>
          <AuthProvider>
            <AppShell>{children}</AppShell>
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
