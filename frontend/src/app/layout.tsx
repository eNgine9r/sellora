import type { Metadata, Viewport } from "next";
import { AppShell } from "@/components/app-shell";
import { QueryProvider } from "@/providers/query-provider";
import { AuthProvider } from "@/stores/auth.store";
import { ThemeProvider } from "@/providers/theme-provider";
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
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#080812",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="overflow-x-hidden bg-[#080812]">
      <body className="min-w-0 overflow-x-hidden bg-[#F8F7FC] antialiased">
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var m=localStorage.getItem('sellora.theme-mode')||'system';var d=window.matchMedia('(prefers-color-scheme: dark)').matches;var t=m==='dark'||(m==='system'&&d)?'dark':'light';document.documentElement.classList.add(t);document.documentElement.dataset.theme=t;}catch(e){document.documentElement.classList.add('light');}})();`,
          }}
        />
        <ThemeProvider>
          <QueryProvider>
            <AuthProvider>
              <AppShell>{children}</AppShell>
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
