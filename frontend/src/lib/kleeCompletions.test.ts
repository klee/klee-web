import { describe, expect, test } from "vitest"
import { COMPLETIONS } from "./kleeCompletions"

describe("KLEE completion specs", () => {
  test("includes klee_make_symbolic as a snippet with the shared sizeof pattern", () => {
    const item = COMPLETIONS.find((c) => c.label === "klee_make_symbolic")
    expect(item).toBeDefined()
    expect(item?.snippet).toBe(true)
    expect(item?.insertText).toContain("sizeof(${1:var})")
    expect(item?.insertText).toContain('"${2:name}"')
  })

  test("includes the core intrinsics and a curated C entry", () => {
    const labels = COMPLETIONS.map((c) => c.label)
    for (const l of [
      "klee_assume",
      "klee_assert",
      "klee_range",
      "printf",
      "#include <klee/klee.h>",
    ]) {
      expect(labels).toContain(l)
    }
  })

  test("labels are unique", () => {
    const labels = COMPLETIONS.map((c) => c.label)
    expect(new Set(labels).size).toBe(labels.length)
  })

  test("every snippet spec carries a tab-stop", () => {
    for (const c of COMPLETIONS) {
      if (c.snippet) expect(c.insertText).toContain("${")
    }
  })

  test("every spec has a known kind", () => {
    const kinds = new Set(["snippet", "function", "module"])
    for (const c of COMPLETIONS) expect(kinds.has(c.kind)).toBe(true)
  })
})
