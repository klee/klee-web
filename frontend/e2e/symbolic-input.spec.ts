import { test, expect } from "@playwright/test";

// The fake runner ignores flags, so the meaningful check is that enabling a spec in
// the panel actually reaches the request. This drives the whole path: opening the
// details panel, the enable toggle, the numeric field, and the submit body carrying
// the structured sym_stdin object.
test("enabling symbolic stdin threads it into the submit request", async ({ page }) => {
  await page.goto("/");

  await page.getByText("Symbolic input").click();

  await page.getByRole("checkbox", { name: "stdin" }).check();
  await page.getByLabel("stdin bytes").fill("16");

  const submit = page.waitForRequest((r) => r.url().endsWith("/jobs") && r.method() === "POST");
  await page.getByRole("button", { name: "Run" }).click();
  const body = (await submit).postDataJSON();

  expect(body.flags.sym_stdin).toEqual({ size: 16 });
});
