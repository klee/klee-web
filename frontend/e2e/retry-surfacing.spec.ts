import { test, expect } from "@playwright/test"

test("attempt badge stays hidden on a first-attempt run", async ({ page }) => {
  await page.goto("/")
  await page.getByRole("button", { name: "Run" }).click()

  await expect(
    page.getByRole("button", { name: "Test cases (3)" }),
  ).toBeVisible({ timeout: 90_000 })

  // get_sign runs once and completes, so there is no retry to announce.
  await expect(page.getByText(/Attempt \d of 3/)).toHaveCount(0)
})

test("the ?debug panel surfaces the raw job state", async ({ page }) => {
  await page.goto("/?debug")

  const panel = page.getByRole("region", { name: "Debug panel" })
  await expect(panel).toBeVisible()
  await expect(panel.getByText("(no job)")).toBeVisible()

  await page.getByRole("button", { name: "Run" }).click()

  // The panel reflects the same poll the results pane uses, so it lands on done.
  await expect(panel.getByText("done")).toBeVisible({ timeout: 90_000 })
})

test("the debug panel is absent without ?debug", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByRole("region", { name: "Debug panel" })).toHaveCount(0)
})
