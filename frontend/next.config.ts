import type { NextConfig } from "next";

const API_PATH = "/api/v1";

function apiUpstream(): string | null {
  // Retain the current deployment setting while allowing a server-only setting
  // for new installations. The browser always receives the same-origin path.
  // Disposable QA preview only. This branch must never be merged to main.
  // Override branch env to protect the live Raspberry API from QA requests.
  if (process.env.VERCEL_ENV === "production") {
    throw new Error("QA-only staging branch cannot deploy to production");
  }
  const qaPreviewUpstream = process.env.VERCEL_ENV === "preview"
    ? "https://btc-radar.tail7f9b04.ts.net/sellora-qa-20261025/api/v1"
    : null;
  const configured = (
    qaPreviewUpstream ??
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

const upstreamConfig: NextConfig = upstream
  ? {
      env: {
        NEXT_PUBLIC_API_BASE_URL: API_PATH,
        ...(process.env.VERCEL_ENV === "preview"
          ? { NEXT_PUBLIC_COOKIE_SESSION_AUTH_ENABLED: "true" }
          : {}),
      },
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

const nextConfig: NextConfig = {
  ...upstreamConfig,
  async headers() {
    return [
      ...(upstreamConfig.headers ? await upstreamConfig.headers() : []),
      { source: "/settings/integrations/meta-ads/callback", headers: [
        { key: "Referrer-Policy", value: "no-referrer" },
        { key: "Cache-Control", value: "no-store" },
      ] },
    ];
  },
};
export default nextConfig;
