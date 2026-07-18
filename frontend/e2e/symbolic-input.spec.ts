import { test, expect } from "@playwright/test";

// This test concerns request serialization rather than Runner output. It drives the
// details panel, enable toggle, numeric field, and submit body carrying the structured
// sym_stdin object.
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
