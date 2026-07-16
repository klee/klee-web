import { test, expect, type Page } from "@playwright/test";

const JOB_ID = "33333333-3333-3333-3333-333333333333";

function makeJob(statesCulledForMemory: number) {
  return {
    id: JOB_ID,
    status: "done",
    created_at: "2026-07-16T00:00:00Z",
    result: {
      test_cases: [],
      messages: "KLEE: done\n",
      warnings: "",
      stats: {},
      program_output: "",
      compile_error: null,
      halt_reason: "completed",
      states_culled_for_memory: statesCulledForMemory,
    },
  };
}

async function mockJob(page: Page, statesCulledForMemory: number) {
  await page.route("**/jobs", (route) =>
    route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ job_id: JOB_ID }),
    }),
  );
  await page.route("**/jobs/*", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(makeJob(statesCulledForMemory)),
    }),
  );
}

test("zero memory culls render no count or indicator", async ({ page }) => {
  await mockJob(page, 0);
  await page.goto("/");
  await page.getByRole("button", { name: "Run" }).click();

  const haltBadge = page.getByText("Explored all paths.");
  await expect(haltBadge).toBeVisible();
  expect(await haltBadge.evaluate((element) => element.nextSibling?.textContent)).not.toBe("0");
  await expect(page.getByText(/states? culled for memory/)).toHaveCount(0);
});

test("a positive memory-cull count renders a formatted indicator", async ({ page }) => {
  await mockJob(page, 1234);
  await page.goto("/");
  await page.getByRole("button", { name: "Run" }).click();

  await expect(page.getByText("1,234 states culled for memory", { exact: true })).toBeVisible();
});
