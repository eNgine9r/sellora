// Local production server ownership shared by synthetic integration gates.
import { createRequire } from "node:module";
import { createServer } from "node:net";
import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
export async function integrationRuntime(name) {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
  const output = path.join(root, "artifacts/integrations-onboarding", name);
  await mkdir(output, { recursive: true });
  const require = createRequire(process.env.PLAYWRIGHT_RUNTIME_PACKAGE || import.meta.url);
  const { chromium, expect } = require("@playwright/test");
  const explicitBase = process.env.INTEGRATIONS_TEST_BASE_URL;
  if (explicitBase) {
    const parsed = new URL(explicitBase);
    if (parsed.username || parsed.password || parsed.search || parsed.hash || !["http:", "https:"].includes(parsed.protocol)) throw new Error("Invalid explicit integration test base");
    const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined });
    return { browser, expect, base: parsed.origin, output, close: () => browser.close() };
  }
  const port = await new Promise((resolve, reject) => {
    const probe = createServer(); probe.once("error", reject);
    probe.listen(0, "127.0.0.1", () => { const port = probe.address().port; probe.close(error => error ? reject(error) : resolve(port)); });
  });
  const base = "http://127.0.0.1:" + port;
  const server = spawn(process.execPath, [path.join(root, "frontend/node_modules/next/dist/bin/next"), process.env.INTEGRATIONS_TEST_DEV === "1" ? "dev" : "start", "-p", String(port), "--hostname", "127.0.0.1"], { cwd: path.join(root, "frontend"), env: { ...process.env, NEXT_TELEMETRY_DISABLED: "1" }, stdio: ["ignore", "pipe", "pipe"] });
  let startup = "", failure, browser;
  server.stdout.on("data", chunk => { startup += chunk.toString(); });
  server.stderr.on("data", chunk => process.stderr.write(chunk));
  server.on("error", error => { failure = error; });
  server.on("exit", code => { failure = new Error("Owned Next server exited: " + code); });
  async function close() {
    await browser?.close();
    if (server.exitCode !== null) return;
    await new Promise(resolve => {
      const timer = setTimeout(() => { server.kill("SIGKILL"); }, 5000);
      server.once("exit", () => { clearTimeout(timer); resolve(); });
      server.kill("SIGTERM");
    });
  }
  try {
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt++) {
      if (failure) throw failure;
      if (startup.includes("Ready in")) {
        try { if ((await fetch(base + "/login")).ok) { ready = true; break; } } catch {}
      }
      await new Promise(resolve => setTimeout(resolve, 300));
    }
    if (!ready) throw new Error("Owned production server did not become ready");
    // Playwright's bundled Chromium is the portable default; native path is opt-in.
    browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined });
    return { browser, expect, base, output, close };
  } catch (error) { await close(); throw error; }
}
