import { expect, test, type Page, type TestInfo } from "@playwright/test";

async function attachScreenshot(page: Page, testInfo: TestInfo, name: string) {
  await testInfo.attach(name, {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });
}

test("desktop client loads, runs KLEE, resizes, and restores history", async ({
  page,
  browser,
  browserName,
}, testInfo) => {
  const metadata = {
    github_client_os: process.env.RUNNER_OS ?? process.platform,
    github_client_image: process.env.ImageOS ?? "local",
    github_client_image_version: process.env.ImageVersion ?? "local",
    architecture: process.env.RUNNER_ARCH ?? process.arch,
    playwright_project: testInfo.project.name,
    browser_engine: browserName,
    browser_version: browser.version(),
  };

  console.log(`CLIENT_MATRIX_METADATA ${JSON.stringify(metadata)}`);
  await testInfo.attach("client-metadata", {
    body: Buffer.from(JSON.stringify(metadata, null, 2)),
    contentType: "application/json",
  });

  await page.goto("/");
  await expect(page.locator(".view-lines")).toContainText("get_sign", { timeout: 30_000 });
  await expect(page.getByRole("button", { name: "Run" })).toBeVisible();
  await attachScreenshot(page, testInfo, "01-monaco-loaded");

  await page.getByRole("button", { name: "Run" }).click();
  const testCases = page.getByRole("button", { name: "Test cases (3)" });
  await expect(testCases).toBeVisible({ timeout: 90_000 });
  await expect(page.getByText("Explored all paths.")).toBeVisible();
  await attachScreenshot(page, testInfo, "02-three-case-result");

  await page.setViewportSize({ width: 1024, height: 768 });
  await expect(page.getByRole("button", { name: "Run" })).toBeInViewport();
  await expect(testCases).toBeInViewport();
  await attachScreenshot(page, testInfo, "03-resized-desktop");

  await page.reload();
  await expect(page.locator(".view-lines")).toContainText("get_sign", { timeout: 30_000 });
  await page.getByRole("button", { name: "History" }).click();
  await expect(page.getByTestId("history-entry")).toHaveCount(1);
  await attachScreenshot(page, testInfo, "04-history-restored");
});
