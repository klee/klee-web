import { test, expect } from "@playwright/test";

const JOB_ID = "22222222-2222-2222-2222-222222222222";

test("running wall time excludes time spent queued", async ({ page }) => {
  const now = new Date("2026-07-15T12:00:00Z");
  const createdAt = new Date(now.getTime() - 120_000).toISOString();
  const startedAt = now.toISOString();
  let polls = 0;

  await page.clock.setFixedTime(now);

  await page.route("**/jobs", (route) =>
    route.request().method() === "POST"
      ? route.fulfill({ status: 202, json: { job_id: JOB_ID } })
      : route.continue(),
  );
  await page.route(`**/jobs/${JOB_ID}`, (route) => {
    polls += 1;
    return route.fulfill({
      json: {
        id: JOB_ID,
        status: polls === 1 ? "pending" : "running",
        created_at: createdAt,
        started_at: polls === 1 ? null : startedAt,
      },
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Run" }).click();

  await expect(page.getByText("Job queued, waiting for runner...")).toBeVisible();
  await expect(page.getByText("Running...")).toBeVisible();
  await expect(page.getByText("0:00", { exact: true })).toBeVisible();
  await expect(page.getByText("Time limit reached", { exact: false })).not.toBeVisible();
});
