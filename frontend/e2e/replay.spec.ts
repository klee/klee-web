import { expect, test } from "@playwright/test";

test("disabling replay threads the setting into the submit request", async ({ page }) => {
  await page.goto("/");

  const replay = page.getByRole("checkbox", { name: "replay" });
  await expect(replay).toBeChecked();
  await replay.uncheck();

  const submit = page.waitForRequest((request) => {
    return request.url().endsWith("/jobs") && request.method() === "POST";
  });
  await page.getByRole("button", { name: "Run" }).click();

  expect((await submit).postDataJSON().flags.enable_replay).toBe(false);
});
