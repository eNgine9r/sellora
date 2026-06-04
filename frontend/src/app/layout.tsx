import type { Metadata } from "next";
import { AppShell } from "@/components/app-shell";
import { QueryProvider } from "@/providers/query-provider";
import { AuthProvider } from "@/stores/auth.store";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sellora",
  description: "CRM for Instagram stores",
  applicationName: "Sellora",
  icons: { icon: "/brand/sellora-icon.svg", apple: "/brand/sellora-icon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>
          <AuthProvider>
            <AppShell>{children}</AppShell>
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
