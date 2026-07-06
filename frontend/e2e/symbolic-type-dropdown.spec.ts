import { test, expect, type Page } from "@playwright/test";

// Mocks a get_sign job so the symbolic values are deterministic, then checks that
// choosing a type re-decodes the raw bytes in place and applies per variable name.

const JOB_ID = "22222222-2222-2222-2222-222222222222";

function makeJob() {
  const tc = (name: string, value: string, bytes_hex: string) => ({
    name,
    inputs: [{ name: "a", value, bytes_hex }],
    error: null,
    path_constraint: null,
  });
  return {
    id: JOB_ID,
    status: "done",
    created_at: "2026-07-01T00:00:00Z",
    result: {
      test_cases: [
        tc("test000001", "0", "00000000"),
        tc("test000002", "16843009", "01010101"),
        tc("test000003", "-2147483648", "00000080"),
      ],
      messages: "",
      warnings: "",
      stats: {},
      program_output: "",
      compile_error: null,
      halt_reason: "completed",
    },
  };
}

async function mock(page: Page) {
  await page.route("**/jobs", (r) =>
    r.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ job_id: JOB_ID }),
    }),
  );
  await page.route("**/jobs/*", (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(makeJob()),
    }),
  );
}

test("choosing a type re-decodes the value for every card of that variable", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Run" }).click();
  await expect(page.getByRole("button", { name: "Test cases (3)" })).toBeVisible();

  // Default is the size heuristic: signed int32.
  await expect(page.getByText("-2147483648", { exact: true })).toBeVisible();

  // Switch variable a to unsigned on the first card; per variable name, so every card re-decodes.
  await page.getByLabel("type for a").first().selectOption("uint");

  await expect(page.getByText("2147483648", { exact: true })).toBeVisible();
  await expect(page.getByText("-2147483648", { exact: true })).toHaveCount(0);
});
