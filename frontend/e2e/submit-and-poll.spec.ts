import { test, expect } from "@playwright/test"

test("submit get_sign.c, poll, and render the test cases", async ({ page }) => {
  await page.goto("/")

  // The editor is pre-seeded with get_sign.c and Run submits that source from
  // React state, so we can run as soon as the app is interactive.
  await page.getByRole("button", { name: "Run" }).click()

  // get_sign is deterministic: three test cases, run completes. Auto-waiting
  // absorbs container startup and the KLEE run.
  await expect(
    page.getByRole("button", { name: "Test cases (3)" }),
  ).toBeVisible({ timeout: 90_000 })

  await expect(page.getByText("Explored all paths.")).toBeVisible()

  for (const value of ["16843009", "-2147483648"]) {
    await expect(page.getByText(value, { exact: true }).first()).toBeVisible()
  }
})
