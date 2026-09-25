import { defineConfig, devices } from "@playwright/test";

/**
 * E2E suite.
 *
 * Expects the Django API to be running (see e2e/README.md); Playwright
 * starts the Next.js server itself. `npm run test:e2e` is the entry point,
 * and CI runs the same command after `manage.py seed_demo`.
 */
const PORT = Number(process.env.E2E_PORT ?? 3100);
const BASE_URL = process.env.E2E_BASE_URL ?? `http://127.0.0.1:${PORT}`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false, // the suite shares one seeded database
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : [["list"]],
  timeout: 45_000,
  expect: { timeout: 10_000 },

  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    locale: "fr-FR",
  },

  // Restores the demo fixtures the suite itself mutates (see e2e/global-setup.ts).
  globalSetup: "./e2e/global-setup.ts",
  projects: [
    // mobile.spec.ts is written for a phone viewport, so it only runs in the
    // mobile project — otherwise the burger menu it asserts on is hidden.
    { name: "desktop", use: { ...devices["Desktop Chrome"] }, testIgnore: /mobile\.spec\.ts/ },
    { name: "mobile", use: { ...devices["Pixel 7"] }, testMatch: /mobile\.spec\.ts/ },
  ],

  webServer: {
    // Build here rather than relying on a pre-existing .next: running the
    // suite against a stale build silently tests yesterday's code.
    command: `npm run build && npm run start -- --port ${PORT}`,
    url: BASE_URL,
    reuseExistingServer: false,
    timeout: 240_000,
    stdout: "ignore",
    stderr: "pipe",
  },
});
