import { describe, expect, test } from "vitest";
import { DEFAULT_EXAMPLE, EXAMPLES } from "./examples";

describe("EXAMPLES", () => {
  test("has all six programs with unique ids, code, and descriptions", () => {
    expect(EXAMPLES).toHaveLength(6);
    const ids = EXAMPLES.map((e) => e.id);
    expect(new Set(ids).size).toBe(6);
    for (const e of EXAMPLES) {
      expect(e.code.trim().length).toBeGreaterThan(0);
      expect(e.description.trim().length).toBeGreaterThan(0);
    }
  });

  test("get_sign is the default seed and contains klee_make_symbolic", () => {
    expect(DEFAULT_EXAMPLE.id).toBe("get_sign");
    expect(DEFAULT_EXAMPLE.code).toContain("klee_make_symbolic");
  });
});
