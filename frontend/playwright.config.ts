import { defineConfig, devices } from "@playwright/test";

const CI = !!process.env.CI;

export default defineConfig({
  testDir: "./e2e",
  forbidOnly: CI,
  retries: CI ? 2 : 0,
  workers: CI ? 1 : undefined,
  reporter: CI ? [["html", { open: "never" }], ["github"]] : "list",
  timeout: 120_000,
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "uv run uvicorn klee_web.main:app --port 8000",
      cwd: "../backend",
      url: "http://localhost:8000/openapi.json",
      reuseExistingServer: !CI,
      timeout: 120_000,
      env: CI ? { KLEE_FAKE_RUNNER: "1" } : {},
    },
    {
      command: "npm run dev",
      url: "http://localhost:5173",
      reuseExistingServer: !CI,
      timeout: 120_000,
    },
  ],
});
