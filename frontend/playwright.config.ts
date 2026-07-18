import { defineConfig, devices } from "@playwright/test";

const CI = !!process.env.CI;

export default defineConfig({
  testDir: "./e2e",
  forbidOnly: CI,
  retries: CI ? 2 : 0,
  workers: 1,
  reporter: CI ? [["html", { open: "never" }], ["github"]] : "list",
  timeout: 120_000,
  use: {
    baseURL: "https://localhost",
    httpCredentials: { username: "admin", password: "test-password" },
    ignoreHTTPSErrors: true,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "bash e2e/serve-stack.sh",
    url: "https://localhost",
    reuseExistingServer: false,
    timeout: 600_000,
    ignoreHTTPSErrors: true,
    gracefulShutdown: { signal: "SIGTERM", timeout: 15_000 },
  },
});
