import { expect, test } from "@playwright/test";

test("controls explain their behavior on hover and keyboard focus", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("link", { name: /Report an issue/ }).hover();
  await expect(
    page.getByRole("tooltip").filter({
      hasText: "Open a public GitHub issue form to report a problem with KLEE Web.",
    }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Run" }).hover();
  await expect(
    page.getByRole("tooltip").filter({
      hasText: "Compiles the C source to LLVM bitcode and runs KLEE",
    }),
  ).toBeVisible();

  await page.getByLabel("time").focus();
  await expect(
    page.getByRole("tooltip").filter({
      hasText: "Total execution budget shared by KLEE and replay (if activated).",
    }),
  ).toBeVisible();

  await page.getByLabel("extra flags").hover();
  const flagsHelp = page.getByRole("tooltip").filter({
    hasText: "--only-output-states-covering-new",
  });
  await expect(flagsHelp).toBeVisible();
  for (const acceptedFlag of [
    "--optimize",
    "--emit-all-errors",
    "--only-output-states-covering-new",
    "--use-cex-cache",
    "--use-branch-cache",
    "--use-independent-solver",
    "--use-forked-solver",
    "=true|false|1|0",
    "--max-forks=N",
    "--max-depth=N",
    "--max-instructions=N",
    "--search=dfs",
    "bfs",
    "random-state",
    "random-path",
    "nurs:covnew",
    "nurs:cpicnt",
    "nurs:depth",
    "nurs:icnt",
    "nurs:md2u",
    "nurs:qc",
    "nurs:rp",
    "--solver-backend=stp|z3",
  ]) {
    await expect(flagsHelp).toContainText(acceptedFlag);
  }

  const maze = page.getByRole("button", { name: "maze.c" });
  const mazeHelp = page.getByRole("tooltip").filter({
    hasText: "Makes 28 movement commands symbolic and searches for a path through the maze.",
  });
  await maze.hover();
  await expect(mazeHelp).toBeVisible();
  await maze.click();
  await expect(mazeHelp).toBeHidden();
  await page.mouse.move(800, 400);
  await expect(mazeHelp).toBeHidden();
  await maze.hover();
  await expect(mazeHelp).toBeVisible();
});

test("execution options explain the data they add to a run", async ({ page }) => {
  await page.goto("/");

  await page.getByLabel("path constraint format").hover();
  await expect(
    page.getByRole("tooltip").filter({
      hasText: "Includes each generated test's path constraint in KQuery format",
    }),
  ).toBeVisible();

  await page.getByLabel("replay").hover();
  await expect(
    page.getByRole("tooltip").filter({
      hasText: "Per-path replay captures readable output for each generated test.",
    }),
  ).toBeVisible();

  const symbolicInput = page.getByText("Symbolic input", { exact: true });
  await symbolicInput.hover();
  await expect(
    page.getByRole("tooltip").filter({
      hasText: "Configure symbolic stdin, files, and command-line arguments",
    }),
  ).toBeVisible();
  await symbolicInput.click();

  await page.getByText("stdin", { exact: true }).hover();
  await expect(
    page.getByRole("tooltip").filter({
      hasText: "Makes the selected number of standard-input bytes symbolic",
    }),
  ).toBeVisible();

  await page.getByText("files", { exact: true }).hover();
  await expect(
    page.getByRole("tooltip").filter({
      hasText: "Creates symbolic files with the selected count and size",
    }),
  ).toBeVisible();

  await page.getByText("args", { exact: true }).hover();
  await expect(
    page.getByRole("tooltip").filter({
      hasText:
        "Generates symbolic command-line arguments using the selected count and length bounds",
    }),
  ).toBeVisible();
});
