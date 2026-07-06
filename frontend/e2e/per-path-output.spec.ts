import { test, expect, type Page } from "@playwright/test"

// Mocked job with two test cases carrying distinct per-path program_output. No KLEE
// needed. Guards that each path's Output foldable shows what that path printed.

const JOB_ID = "22222222-2222-2222-2222-222222222222"

function makeJob() {
  return {
    id: JOB_ID,
    status: "done",
    created_at: "2026-07-01T00:00:00Z",
    result: {
      test_cases: [
        {
          name: "test000001",
          inputs: [{ name: "in", value: "a", bytes_hex: "61" }],
          error: null,
          path_constraint: null,
          program_output: "Hello World!",
        },
        {
          name: "test000002",
          inputs: [{ name: "in", value: "b", bytes_hex: "62" }],
          error: null,
          path_constraint: null,
          program_output: "Goodbye World!",
        },
      ],
      messages: "KLEE: done\n",
      warnings: "",
      stats: { Instructions: 100 },
      program_output: "",
      compile_error: null,
      halt_reason: "completed",
    },
  }
}

async function mockJob(page: Page) {
  await page.route("**/jobs", (r) =>
    r.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ job_id: JOB_ID }),
    }),
  )
  await page.route("**/jobs/*", (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(makeJob()),
    }),
  )
}

test("each test case shows its own per-path output", async ({ page }) => {
  await mockJob(page)
  await page.goto("/")
  await page.getByRole("button", { name: "Run" }).click()

  await expect(page.getByRole("button", { name: "Test cases (2)" })).toBeVisible()

  const outputs = page.locator("summary", { hasText: "Output" })
  await expect(outputs).toHaveCount(2)

  await outputs.nth(0).click()
  await outputs.nth(1).click()
  await expect(page.locator("pre", { hasText: "Hello World!" })).toBeVisible()
  await expect(page.locator("pre", { hasText: "Goodbye World!" })).toBeVisible()
})
