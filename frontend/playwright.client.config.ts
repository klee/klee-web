import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL;

if (!baseURL) {
  throw new Error("PLAYWRIGHT_BASE_URL is required for client compatibility evidence");
}

export default defineConfig({
  testDir: ".",
  testMatch: [
    "**/client-evidence/client-compatibility.spec.ts",
    "**/e2e/monaco-intellisense.spec.ts",
    "**/e2e/program-output-large.spec.ts",
  ],
  forbidOnly: true,
  retries: 0,
  workers: 1,
  timeout: 120_000,
  reporter: [["list"], ["html", { outputFolder: "playwright-client-report", open: "never" }]],
  outputDir: "client-test-results",
  use: {
    baseURL,
    ignoreHTTPSErrors: false,
    trace: "on",
    video: "on",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chrome", use: { ...devices["Desktop Chrome"], channel: "chrome" } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
    { name: "edge", use: { ...devices["Desktop Edge"], channel: "msedge" } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
  ],
});
