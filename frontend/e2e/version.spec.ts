import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";

const KLEE_VERSION = readFileSync(new URL("../../.klee-version", import.meta.url), "utf8").trim();

test("the status bar shows the pinned KLEE version", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText(`KLEE ${KLEE_VERSION}`, { exact: true })).toBeVisible();
});
