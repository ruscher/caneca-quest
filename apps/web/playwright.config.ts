import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { defineConfig, devices } from "@playwright/test";

const PORT = 8790;
// Outside test-results/ (Playwright wipes that folder after the web server starts).
const dataDir = process.env.CANECA_E2E_DATA ?? mkdtempSync(join(tmpdir(), "caneca-e2e-"));
process.env.CANECA_E2E_DATA = dataDir;

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    locale: "pt-BR",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } }, testIgnore: /mobile|screenshots/ },
    { name: "mobile", use: { ...devices["Pixel 7"] }, testMatch: /mobile/ },
    { name: "screenshots", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } }, testMatch: /screenshots/ },
  ],
  webServer: {
    // The real stack: FastAPI serving the production build, with a throwaway data dir.
    command: `uv run --project ../../backend caneca-server --port ${PORT} --data-dir ${dataDir} --static-dir ./dist`,
    url: `http://127.0.0.1:${PORT}/api/health`,
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
