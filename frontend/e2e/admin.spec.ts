import { test, expect } from "@playwright/test";

test.setTimeout(10_000);

test("admin opens separately, reads fleet state, and changes a worker maximum", async ({
  page,
  context,
}) => {
  let liveMaximum = 4;
  let requestedMaximum: number | null = null;
  let queueAvailable = true;
  let capacityError: string | null = null;

  await context.route("**/api/admin/telemetry", (route) =>
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
        queue: queueAvailable ? { name: "klee-jobs", depth: 5 } : null,
      }),
    }),
  );
  await context.route("**/api/admin/stats", (route) =>
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
  await context.route("**/api/admin/workers/*/capacity", async (route) => {
    if (capacityError !== null) {
      await route.fulfill({ status: 503, json: { detail: capacityError } });
      return;
    }
    const body = route.request().postDataJSON() as { max_concurrency: number };
    requestedMaximum = body.max_concurrency;
    liveMaximum = body.max_concurrency;
    await route.fulfill({ status: 204 });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Settings" }).click();
  const adminPagePromise = page.waitForEvent("popup");
  await page.getByRole("link", { name: "Administration" }).click();
  const adminPage = await adminPagePromise;

  await expect(page).toHaveURL("/");
  await expect(adminPage).toHaveURL("/admin");
  await expect(adminPage.getByRole("heading", { name: "Fleet operations" })).toBeVisible();
  await expect(adminPage.getByRole("heading", { name: "worker1@host" })).toBeVisible();
  await expect(adminPage.getByText("Waiting jobs")).toBeVisible();
  await expect(adminPage.getByText("6 waiting")).toBeVisible();
  await expect(adminPage.getByText("4 per worker")).toBeVisible();
  await expect(adminPage.getByText("18 executions")).toBeVisible();

  const capacity = adminPage.getByRole("spinbutton", {
    name: "Maximum concurrency for worker1@host",
  });
  await capacity.fill("");
  await adminPage.getByRole("button", { name: "Apply worker1@host capacity" }).click();
  await adminPage.waitForTimeout(100);
  expect(requestedMaximum).toBeNull();

  await capacity.fill("2");
  await adminPage.getByRole("button", { name: "Apply worker1@host capacity" }).click();

  await expect.poll(() => requestedMaximum).toBe(2);
  await expect(adminPage.getByText("Live maximum 2")).toBeVisible();

  queueAvailable = false;
  await adminPage.reload();
  await expect(adminPage.getByText("Unavailable")).toBeVisible();

  capacityError = "Worker did not respond: worker1@host";
  await capacity.fill("3");
  await adminPage.getByRole("button", { name: "Apply worker1@host capacity" }).click();
  await expect(adminPage.getByText(capacityError)).toBeVisible();
});
