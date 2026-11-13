import { NextResponse, type NextRequest } from "next/server";

const forwarded = ["accept", "authorization", "content-type", "origin", "referer", "x-workspace-id", "x-sellora-platform-mfa"];
const directoryAliases = new Set([
  "/api/v1/platform-admin/workspaces/",
  "/api/v1/platform-admin/workspaces/search/",
  "/api/v1/platform-admin/mfa/verify/",
]);

export function proxy(request: NextRequest) {
  const secret = process.env.NOEVIA_API_VERCEL_AUTOMATION_SECRET;
  const upstream = URL.parse(process.env.SELLORA_API_UPSTREAM_URL ?? "");
  if (!secret || upstream?.protocol !== "https:" || upstream.username || upstream.password
    || upstream.hostname !== "sellora-platform-staging-api.vercel.app"
    || upstream.pathname !== "/api/v1" || upstream.search || upstream.hash) {
    return NextResponse.json({ detail: "Staging API unavailable" }, { status: 503 });
  }

  const path = request.nextUrl.pathname;
  const destination = new URL(upstream.origin);
  destination.pathname = directoryAliases.has(path) ? path.slice(0, -1) : path;
  destination.search = request.nextUrl.search;
  const headers = new Headers();
  for (const name of forwarded) {
    const value = request.headers.get(name);
    if (value !== null) headers.set(name, value);
  }
  const refresh = request.cookies.get("sellora_session_refresh");
  if (refresh) headers.set("cookie", "sellora_session_refresh=" + encodeURIComponent(refresh.value));
  headers.set("x-vercel-protection-bypass", secret);
  return NextResponse.rewrite(destination, { request: { headers } });
}

export const config = { matcher: "/api/v1/:path*" };
