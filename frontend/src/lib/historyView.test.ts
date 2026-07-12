import { describe, expect, test } from "vitest";
import { historyLabel, relativeTime, statusGlyph } from "./historyView";

describe("historyLabel", () => {
  test("uses a // title: comment when present", () => {
    expect(historyLabel("// title: Two-branch demo\nint main() {}\n")).toBe("Two-branch demo");
  });
  test("accepts block and header-star forms, case-insensitive", () => {
    expect(historyLabel("/* TITLE: My Test */\n")).toBe("My Test");
    expect(historyLabel("/*\n * title: Regex matcher\n */\nint main(){}\n")).toBe("Regex matcher");
  });
  test("does not match title: inside code or strings", () => {
    expect(historyLabel('int main() {\n  printf("title: x");\n}\n')).toBe('printf("title: x");');
  });
  test("falls back to the first real line, skipping boilerplate", () => {
    const code =
      "/*\n * a comment\n */\n#include <klee/klee.h>\n\nint get_sign(int x) {\n  return x;\n}\nint main() {}\n";
    expect(historyLabel(code)).toBe("int get_sign(int x) {");
  });
  test("skips the main signature to the first statement", () => {
    expect(historyLabel('#include <stdio.h>\nint main() {\n  printf("hi");\n}\n')).toBe(
      'printf("hi");',
    );
  });
  test("truncates long labels", () => {
    const long = "int " + "x".repeat(60) + ";";
    expect(historyLabel(long)).toBe(long.slice(0, 45) + "...");
  });
  test("boilerplate-only falls back to the first non-comment line, empty is (empty)", () => {
    expect(historyLabel("#include <stdio.h>\nint main() {}\n")).toBe("#include <stdio.h>");
    expect(historyLabel("// just a comment")).toBe("(empty)");
    expect(historyLabel("")).toBe("(empty)");
  });
});

describe("relativeTime", () => {
  test("buckets by magnitude", () => {
    expect(relativeTime(1000, 1000)).toBe("just now");
    expect(relativeTime(1000, 31_000)).toBe("30s ago");
    expect(relativeTime(0, 5 * 60_000)).toBe("5m ago");
    expect(relativeTime(0, 3 * 3_600_000)).toBe("3h ago");
    expect(relativeTime(0, 2 * 86_400_000)).toBe("2d ago");
  });
});

describe("statusGlyph", () => {
  test("maps each status to a glyph and label", () => {
    expect(statusGlyph("completed").glyph).toBe("✓");
    expect(statusGlyph("failed").label).toBe("Failed");
  });
});
