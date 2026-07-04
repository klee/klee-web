import { describe, expect, test } from "vitest"
import type { Job } from "../api/jobs"
import { deriveHistoryStatus, historyLabel, relativeTime, statusGlyph } from "./historyView"

describe("historyLabel", () => {
  test("uses a // title: comment when present", () => {
    expect(historyLabel("// title: Two-branch demo\nint main() {}\n")).toBe("Two-branch demo")
  })
  test("accepts block and header-star forms, case-insensitive", () => {
    expect(historyLabel("/* TITLE: My Test */\n")).toBe("My Test")
    expect(historyLabel("/*\n * title: Regex matcher\n */\nint main(){}\n")).toBe("Regex matcher")
  })
  test("does not match title: inside code or strings", () => {
    expect(historyLabel('int main() {\n  printf("title: x");\n}\n')).toBe('printf("title: x");')
  })
  test("falls back to the first real line, skipping boilerplate", () => {
    const code =
      "/*\n * a comment\n */\n#include <klee/klee.h>\n\nint get_sign(int x) {\n  return x;\n}\nint main() {}\n"
    expect(historyLabel(code)).toBe("int get_sign(int x) {")
  })
  test("skips the main signature to the first statement", () => {
    expect(historyLabel('#include <stdio.h>\nint main() {\n  printf("hi");\n}\n')).toBe('printf("hi");')
  })
  test("truncates long labels", () => {
    const long = "int " + "x".repeat(60) + ";"
    expect(historyLabel(long)).toBe(long.slice(0, 45) + "...")
  })
  test("boilerplate-only falls back to the first non-comment line, empty is (empty)", () => {
    expect(historyLabel("#include <stdio.h>\nint main() {}\n")).toBe("#include <stdio.h>")
    expect(historyLabel("// just a comment")).toBe("(empty)")
    expect(historyLabel("")).toBe("(empty)")
  })
})

describe("relativeTime", () => {
  test("buckets by magnitude", () => {
    expect(relativeTime(1000, 1000)).toBe("just now")
    expect(relativeTime(1000, 31_000)).toBe("30s ago")
    expect(relativeTime(0, 5 * 60_000)).toBe("5m ago")
    expect(relativeTime(0, 3 * 3_600_000)).toBe("3h ago")
    expect(relativeTime(0, 2 * 86_400_000)).toBe("2d ago")
  })
})

describe("statusGlyph", () => {
  test("maps each status to a glyph and label", () => {
    expect(statusGlyph("completed").glyph).toBe("✓")
    expect(statusGlyph("failed").label).toBe("Failed")
  })
})

describe("deriveHistoryStatus", () => {
  const base: Job = {
    id: "j",
    status: "done",
    created_at: "2026-07-04T00:00:00Z",
    result: null,
  }
  test("failed job maps to failed", () => {
    expect(deriveHistoryStatus({ ...base, status: "failed" })).toBe("failed")
  })
  test("non-terminal job maps to null", () => {
    expect(deriveHistoryStatus({ ...base, status: "running" })).toBeNull()
  })
  test("compile error takes precedence", () => {
    const job = {
      ...base,
      result: {
        test_cases: [],
        messages: "",
        warnings: "",
        stats: {},
        program_output: "",
        compile_error: "boom",
      },
    } as Job
    expect(deriveHistoryStatus(job)).toBe("compile_error")
  })
  test("done maps to its halt reason, defaulting to completed", () => {
    const mk = (halt: string | undefined) =>
      ({
        ...base,
        result: {
          test_cases: [],
          messages: "",
          warnings: "",
          stats: {},
          program_output: "",
          halt_reason: halt,
        },
      }) as Job
    expect(deriveHistoryStatus(mk("max_time"))).toBe("max_time")
    expect(deriveHistoryStatus(mk("cancelled"))).toBe("cancelled")
    expect(deriveHistoryStatus(mk(undefined))).toBe("completed")
  })
})
