import { test, expect } from "@playwright/test";

test.setTimeout(10_000);

test("admin reads fleet state and changes a worker maximum", async ({ page }) => {
  let liveMaximum = 4;
  let requestedMaximum: number | null = null;

  await page.route("**/api/admin/telemetry", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        max_worker_concurrency: 4,
        workers: [
          {
            name: "worker1@host",
            concurrency: 3,
            max_concurrency: liveMaximum,
            active: 2,
            reserved: 1,
          },
        ],
        queue: { name: "klee-jobs", depth: 5 },
      }),
    }),
  );
  await page.route("**/api/admin/stats", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        outcomes: {
          completed: 12,
          max_time: 3,
          cancelled: 1,
          compile_error: 2,
          failed: 0,
        },
        cache_hits: 5,
        test_cases_generated: 120,
        instructions_executed: 10_000,
      }),
    }),
  );
  await page.route("**/api/admin/workers/*/capacity", async (route) => {
    const body = route.request().postDataJSON() as { max_concurrency: number };
    requestedMaximum = body.max_concurrency;
    liveMaximum = body.max_concurrency;
    await route.fulfill({ status: 204 });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Settings" }).click();
  await page.getByRole("link", { name: "Administration" }).click();

  await expect(page.getByRole("heading", { name: "Fleet operations" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "worker1@host" })).toBeVisible();
  await expect(page.getByText("5 waiting")).toBeVisible();
  await expect(page.getByText("4 per worker")).toBeVisible();
  await expect(page.getByText("18 submissions")).toBeVisible();

  const capacity = page.getByRole("spinbutton", {
    name: "Maximum concurrency for worker1@host",
  });
  await capacity.fill("2");
  await page.getByRole("button", { name: "Apply worker1@host capacity" }).click();

  await expect.poll(() => requestedMaximum).toBe(2);
  await expect(page.getByText("Live maximum 2")).toBeVisible();
});
