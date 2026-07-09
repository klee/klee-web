import { test, expect } from "@playwright/test";

const JOB_ID = "11111111-1111-1111-1111-111111111111";

const running = { id: JOB_ID, status: "running" };

const cancelledEmpty = {
  id: JOB_ID,
  status: "done",
  result: {
    test_cases: [],
    messages: "",
    warnings: "",
    stats: {},
    program_output: "",
    halt_reason: "cancelled",
  },
};

const cancelledWithPartials = {
  id: JOB_ID,
  status: "done",
  result: {
    test_cases: [
      { name: "test000001", inputs: [{ name: "x", value: "0", bytes_hex: "00000000" }] },
      { name: "test000002", inputs: [{ name: "x", value: "1", bytes_hex: "01000000" }] },
    ],
    messages: "",
    warnings: "",
    stats: {},
    program_output: "",
    halt_reason: "cancelled",
  },
};

// The cancel eager-flips the job to done with an empty result, then the executor
// enriches it with the partials. The UI must poll past the flip and render them on
// its own, so this test never fires a focus event.
test("cancel surfaces partial test cases without a tab switch", async ({ page }) => {
  let cancelled = false;
  let pollsAfterCancel = 0;

  await page.route("**/jobs", (route) =>
    route.request().method() === "POST"
      ? route.fulfill({ status: 202, json: { job_id: JOB_ID } })
      : route.continue(),
  );

  await page.route(`**/jobs/${JOB_ID}/cancel`, (route) => {
    cancelled = true;
    return route.fulfill({ status: 202, json: cancelledEmpty });
  });

  await page.route(`**/jobs/${JOB_ID}`, (route) => {
    if (!cancelled) return route.fulfill({ json: running });
    pollsAfterCancel += 1;
    return route.fulfill({ json: pollsAfterCancel <= 2 ? cancelledEmpty : cancelledWithPartials });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Run" }).click();
  await page.getByRole("button", { name: "Cancel" }).click();

  await expect(page.getByText("Cancelled by user. Some paths may be unexplored.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Test cases (2)" })).toBeVisible();
});
