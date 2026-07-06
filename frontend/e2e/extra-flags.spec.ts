import { test, expect } from "@playwright/test";

// The real backend validates extra_flags (KLEE_FAKE_RUNNER in CI fakes only the run,
// not the request validation), so a flag that is not on the allowlist is a genuine
// 422 that never reaches the runner. This drives the whole path: the flag input,
// submit, the 422, and the submit-rejected state rendering the server's reason.
test("a flag not on the allowlist is rejected with a readable reason", async ({ page }) => {
  await page.goto("/");

  const flags = page.getByLabel("extra flags");
  await expect(flags).toBeVisible();
  await flags.fill("--output-dir=/etc");

  await page.getByRole("button", { name: "Run" }).click();

  await expect(page.getByText(/could not be started/i)).toBeVisible();
  await expect(page.getByText("--output-dir is not an allowed flag")).toBeVisible();
});
