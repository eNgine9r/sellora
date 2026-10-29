import { defineConfig } from "@playwright/test";
import path from "node:path";

const database = new URL(process.env.DATABASE_URL ?? "postgresql://invalid/invalid");
if (process.env.SELLORA_DIRECT_CONFLICT_E2E !== "YES" ||
    !["postgresql:", "postgresql+psycopg:"].includes(database.protocol) ||
    !["127.0.0.1", "localhost", "[::1]"].includes(database.hostname) ||
    database.pathname !== "/sellora_direct_client_conflict_e2e_isolated" || database.search || database.hash) {
  throw new Error("Direct E2E requires explicit opt-in and the exact loopback disposable PostgreSQL database");
}

export default defineConfig({
  testDir: "./e2e/direct-client-conflict",
  outputDir: "./.direct-client-conflict-results",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3100",
    browserName: "chromium",
    screenshot: "only-on-failure",
    trace: "off",
    serviceWorkers: "block",
  },
  projects: [
    { name: "desktop", use: { viewport: { width: 1440, height: 1000 } } },
    { name: "mobile", use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
  webServer: [
    {
      command: "python -m uvicorn app.main:app --host 127.0.0.1 --port 8100",
      cwd: path.resolve(__dirname, "../backend"),
      url: "http://127.0.0.1:8100/health",
      reuseExistingServer: false,
      stdout: "pipe",
      timeout: 30_000,
      env: {
        ENVIRONMENT: "development",
        META_INSTAGRAM_WEBHOOK_WORKER_ENABLED: "false",
        META_INSTAGRAM_WEBHOOK_PROCESSING_ENABLED: "false",
        META_INSTAGRAM_SEND_ENABLED: "false",
        META_INSTAGRAM_AUTO_ANALYSIS_ENABLED: "false",
        META_INSTAGRAM_AUTO_SEND_ENABLED: "false",
        META_SYNC_ENABLED: "false",
        AI_FEATURE_ENABLED: "false",
        AI_CUSTOMER_DATA_EXTRACTION_ENABLED: "false",
        STAGING_NOVA_POSHTA_ALLOW_WRITES: "false",
        SELLORA_COOKIE_SESSIONS_ENABLED: "true",
        SELLORA_LEGACY_AUTH_ENABLED: "false",
        SELLORA_CORS_ALLOWED_ORIGINS: "http://127.0.0.1:3100",
        META_GRAPH_API_BASE_URL: "http://127.0.0.1:9",
        AI_API_BASE_URL: "http://127.0.0.1:9",
        NOVA_POSHTA_API_URL: "http://127.0.0.1:9",
      },
    },
    {
      command: "node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port 3100",
      url: "http://127.0.0.1:3100/login",
      reuseExistingServer: false,
      stdout: "pipe",
      timeout: 120_000,
      env: {
        NEXT_PUBLIC_COOKIE_SESSION_AUTH_ENABLED: "true",
        SELLORA_API_UPSTREAM_URL: "http://127.0.0.1:8100/api/v1",
        NEXT_PUBLIC_API_BASE_URL: "/api/v1",
        NEXT_TELEMETRY_DISABLED: "1",
      },
    },
  ],
});
