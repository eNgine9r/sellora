import { defineConfig } from "@playwright/test";
import browserConfig from "./playwright.direct-client-conflict.config";

const servers = browserConfig.webServer;
if (!Array.isArray(servers)) throw new Error("Expected the isolated frontend and backend browser servers");

export default defineConfig({
  ...browserConfig,
  testDir: "./e2e/platform-admin",
  outputDir: "./test-results/platform-admin",
  webServer: servers.map((server) => ({
    ...server,
    env: { ...server.env, SELLORA_PLATFORM_ADMIN_ENABLED: "true" },
  })),
});
