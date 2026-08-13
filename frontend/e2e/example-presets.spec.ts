import { expect, test, type Page } from "@playwright/test";

async function selectExample(page: Page, name: string) {
  await page.getByRole("button", { name }).click();
}

async function expectBasePreset(page: Page, time: string, replay: boolean, extraFlags: string) {
  await expect(page.getByLabel("time")).toHaveValue(time);
  await expect(page.getByLabel("memory")).toHaveValue("512");
  await expect(page.getByLabel("path constraint format")).toHaveValue("none");
  await expect(page.getByLabel("replay")).toBeChecked({ checked: replay });
  await expect(page.getByLabel("extra flags")).toHaveValue(extraFlags);
}

test("examples replace the current settings with complete recommended presets", async ({
  page,
}) => {
  await page.goto("/");

  await selectExample(page, "regexp.c");
  await expectBasePreset(page, "60", false, "--only-output-states-covering-new");
  await expect(page.getByText("active")).toHaveCount(0);

  await selectExample(page, "maze.c");
  await expectBasePreset(page, "60", true, "--only-output-states-covering-new");
  await expect(page.getByText("active")).toHaveCount(0);

  await page.getByText("Symbolic input", { exact: true }).click();
  await page.getByLabel("stdin").check();
  await expect(page.getByLabel("stdin bytes")).toHaveValue("8");

  await selectExample(page, "sym_input.c");
  await expectBasePreset(page, "10", true, "");
  await expect(page.getByText("1 active")).toBeVisible();
  const stdin = page.getByLabel("stdin", { exact: true });
  const stdinBytes = page.getByLabel("stdin bytes");
  await expect(stdin).toBeVisible();
  await expect(stdin).toBeChecked();
  await expect(stdinBytes).toBeVisible();
  await expect(stdinBytes).toHaveValue("1");

  await selectExample(page, "hello_world.c");
  await expectBasePreset(page, "10", true, "");
  await expect(page.getByText("active")).toHaveCount(0);
});
