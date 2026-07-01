import { test, expect, type Page } from "@playwright/test"

// These specs pin the job response with page.route so program_output is an exact
// string, no backend or KLEE needed. They guard the large-output layout bug: a long
// line with no break opportunity used to blow out the flex width and shove the whole
// Results panel off-screen.

const JOB_ID = "11111111-1111-1111-1111-111111111111"

function makeJob(programOutput: string) {
  return {
    id: JOB_ID,
    status: "done",
    created_at: "2026-07-01T00:00:00Z",
    result: {
      test_cases: [
        {
          name: "test000001",
          inputs: [{ name: "a", value: "0", bytes_hex: "00000000" }],
          error: null,
          path_constraint: null,
        },
        {
          name: "test000002",
          inputs: [{ name: "a", value: "16843009", bytes_hex: "01010101" }],
          error: null,
          path_constraint: null,
        },
      ],
      messages: "KLEE: done\n",
      warnings: "",
      stats: { Instructions: 100 },
      program_output: programOutput,
      compile_error: null,
      halt_reason: "completed",
    },
  }
}

async function mockJob(page: Page, programOutput: string) {
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
      body: JSON.stringify(makeJob(programOutput)),
    }),
  )
}

test("a long unbreakable output line keeps the Results panel on-screen", async ({ page }) => {
  // One 10k-char line with no spaces or newlines: the exact shape that blew out the layout.
  await mockJob(page, "hi".repeat(5000))
  await page.goto("/")
  await page.getByRole("button", { name: "Run" }).click()

  const tab = page.getByRole("button", { name: "Test cases (2)" })
  await expect(tab).toBeVisible()

  await page.locator("summary", { hasText: "Program output" }).click()

  const viewport = page.viewportSize()!
  const box = await tab.boundingBox()
  expect(box).not.toBeNull()
  // The whole Results panel must stay within the viewport, not be pushed off the right edge.
  expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width)
})

test("the program-output header shows a line count", async ({ page }) => {
  await mockJob(page, "hi\n".repeat(1500))
  await page.goto("/")
  await page.getByRole("button", { name: "Run" }).click()

  await expect(page.getByRole("button", { name: "Test cases (2)" })).toBeVisible()
  await expect(page.locator("summary", { hasText: "Program output" })).toContainText(
    "1,500 lines",
  )
})
