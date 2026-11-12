import { randomBytes } from "node:crypto";
import { defineConfig } from "@playwright/test";
import browserConfig from "./playwright.direct-client-conflict.config";

const servers = browserConfig.webServer;
const fixtureSigningKey = randomBytes(48).toString("base64url");
if (!Array.isArray(servers)) throw new Error("Expected the isolated frontend and backend browser servers");

export default defineConfig({
  ...browserConfig,
  testDir: "./e2e/platform-admin",
  outputDir: "./test-results/platform-admin",
  webServer: servers.map((server) => ({
    ...server,
    env: {
      ...server.env,
      JWT_SECRET: fixtureSigningKey,
      SELLORA_PLATFORM_ADMIN_ENABLED: "true",
      SELLORA_PRODUCT_USAGE_CAPTURE_ENABLED: "true",
      SELLORA_PRODUCT_USAGE_COVERAGE_FROM: "2020-01-01T00:00:00Z",
    },
  })),
});
