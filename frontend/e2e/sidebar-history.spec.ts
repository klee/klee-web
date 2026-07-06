import { test, expect, type Page } from "@playwright/test";

// The sidebar and history flows are frontend + localStorage behavior, so we mock
// the job API (as symbolic-type-dropdown.spec does) for a fast, runner-independent
// run. Each POST returns a fresh job id, so distinct examples produce distinct
// history rows (addRun dedups only when the newest entry is identical).

function makeJob(id: string) {
  const tc = (name: string, value: string, bytes_hex: string) => ({
    name,
    inputs: [{ name: "a", value, bytes_hex }],
    error: null,
    path_constraint: null,
  });
  return {
    id,
    status: "done",
    created_at: "2026-07-04T00:00:00Z",
    result: {
      test_cases: [tc("test000001", "0", "00000000"), tc("test000002", "1", "01000000")],
      messages: "",
      warnings: "",
      stats: {},
      program_output: "",
      compile_error: null,
      halt_reason: "completed",
    },
  };
}

async function mockJobs(page: Page) {
  let n = 0;
  await page.route("**/jobs", (route) => {
    n += 1;
    route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ job_id: `job-${n}` }),
    });
  });
  await page.route("**/jobs/*", (route) => {
    const id = route.request().url().split("/").pop() ?? "job";
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(makeJob(id)),
    });
  });
}

async function runExample(page: Page, label: string) {
  await page.getByRole("button", { name: "Examples" }).click();
  await page.getByRole("button", { name: label }).click();
  await page.getByRole("button", { name: "Run" }).click();
  await expect(page.getByRole("button", { name: /Test cases/ })).toBeVisible();
}

test("running an example records a titled history entry, and restore refetches it", async ({
  page,
}) => {
  await mockJobs(page);
  await page.goto("/");

  // Fresh browser: empty history, plus the teaching hint (visible on every tab).
  await page.getByRole("button", { name: "History" }).click();
  await expect(page.getByText("No runs yet. Hit Run to start your history.")).toBeVisible();
  await expect(page.getByText("to name a run in your history.")).toBeVisible();

  // Run the maze example; its `// title:` comment becomes the history label.
  await runExample(page, "maze.c");
  await page.getByRole("button", { name: "History" }).click();
  await expect(page.getByTestId("history-entry")).toHaveCount(1);
  await expect(page.getByTestId("history-entry")).toContainText("Symbolic maze");

  // Loading another example resets the current job, so the results panel empties.
  await page.getByRole("button", { name: "Examples" }).click();
  await page.getByRole("button", { name: "hello_world.c" }).click();
  await expect(page.getByRole("button", { name: /Test cases/ })).toHaveCount(0);

  // Restoring the maze run refetches its result: the test cases come back.
  await page.getByRole("button", { name: "History" }).click();
  await page.getByTestId("history-entry").filter({ hasText: "Symbolic maze" }).click();
  await expect(page.getByRole("button", { name: /Test cases/ })).toBeVisible();
});

test("history entries can be deleted and cleared", async ({ page }) => {
  await mockJobs(page);
  await page.goto("/");

  await runExample(page, "maze.c");
  await runExample(page, "hello_world.c");

  await page.getByRole("button", { name: "History" }).click();
  await expect(page.getByTestId("history-entry")).toHaveCount(2);

  // Delete the maze row; the hello_world row remains.
  await page
    .getByRole("listitem")
    .filter({ hasText: "Symbolic maze" })
    .getByRole("button", { name: "Delete run" })
    .click();
  await expect(page.getByTestId("history-entry")).toHaveCount(1);
  await expect(page.getByTestId("history-entry")).toContainText("Hello world");

  // Clear empties the list back to the starting state.
  await page.getByRole("button", { name: "Clear" }).click();
  await expect(page.getByText("No runs yet. Hit Run to start your history.")).toBeVisible();
});
