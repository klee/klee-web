import { test, expect } from "@playwright/test"

// The only e2e that drives the Monaco editor directly. Monaco loads via the
// wrapper (from a CDN), so we first wait for it to render the seeded program
// before typing, otherwise the keystrokes race the editor becoming interactive.
test("a KLEE intrinsic autocompletes and expands as a snippet", async ({ page }) => {
  await page.goto("/")

  // Monaco is ready once it has rendered the seeded get_sign.c.
  await expect(page.locator(".view-lines")).toContainText("get_sign", { timeout: 30_000 })

  // Clear the seed so the snippet assertion cannot match pre-existing text.
  await page.locator(".monaco-editor").first().click()
  await page.keyboard.press("ControlOrMeta+A")
  await page.keyboard.press("Delete")

  // Type a prefix; Monaco auto-opens the widget and filters our provider's list
  // down to the one intrinsic. Wait for the `visible` class it adds when open.
  await page.keyboard.type("klee_ma", { delay: 40 })

  const suggest = page.locator(".suggest-widget.visible")
  await expect(suggest).toBeVisible()
  await expect(suggest).toContainText("klee_make_symbolic")

  // Accept the highlighted suggestion; the snippet expands with default placeholders.
  await page.keyboard.press("Tab")
  await expect(page.locator(".view-lines")).toContainText("sizeof(var)")
})
