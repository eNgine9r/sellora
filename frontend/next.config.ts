import type { NextConfig } from "next";

const API_PATH = "/api/v1";

function apiUpstream(): string | null {
  // Retain the current deployment setting while allowing a server-only setting
  // for new installations. The browser always receives the same-origin path.
  const configured = (
    process.env.SELLORA_API_UPSTREAM_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    ""
  ).trim();
  if (!configured || configured.startsWith("/")) return null;

  const url = new URL(configured);
  if (
    !["https:", "http:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash
  ) {
    throw new Error("Invalid Sellora API upstream configuration");
  }
  return url.toString().replace(/\/+$/, "");
}

const upstream = apiUpstream();

const nextConfig: NextConfig = upstream
  ? {
      env: { NEXT_PUBLIC_API_BASE_URL: API_PATH },
      async rewrites() {
        return [
          {
            source: API_PATH + "/:path*",
            destination: upstream + "/:path*",
          },
        ];
      },
      async headers() {
        return [
          {
            source: "/:path*",
            headers: [
              { key: "X-Content-Type-Options", value: "nosniff" },
              { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
              { key: "X-Frame-Options", value: "DENY" },
              {
                // Report only: strict enforcement would break the current inline Next.js bootstrap.
                key: "Content-Security-Policy-Report-Only",
                value: [
                  "default-src 'self'",
                  "script-src 'self'",
                  "style-src 'self'",
                  "img-src 'self' https: data: blob:",
                  "connect-src 'self'",
                  "font-src 'self' data:",
                  "object-src 'none'",
                  "base-uri 'self'",
                  "form-action 'self'",
                ].join("; "),
              },
              { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
            ],
          },
          {
            source: API_PATH + "/:path*",
            headers: [{ key: "Cache-Control", value: "no-store" }],
          },
        ];
      },
    }
  : {};

export default nextConfig;
