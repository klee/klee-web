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

  test("provides the approved complete settings preset for every example", () => {
    expect(Object.fromEntries(EXAMPLES.map((example) => [example.id, example.flags]))).toEqual({
      get_sign: preset({ max_time: 10 }),
      regexp: preset({
        max_time: 60,
        enable_replay: false,
        extra_flags: "--only-output-states-covering-new",
      }),
      maze: preset({
        max_time: 60,
        extra_flags: "--only-output-states-covering-new",
      }),
      hello_world: preset({ max_time: 10 }),
      sym_input: preset({ max_time: 10, sym_stdin: { size: 1 } }),
      double_free: preset({ max_time: 10 }),
    });
  });
});

function preset(overrides: Record<string, unknown>) {
  return {
    max_time: 10,
    max_memory: 512,
    enable_replay: true,
    query_format: "none",
    extra_flags: "",
    sym_stdin: null,
    sym_files: null,
    sym_args: null,
    ...overrides,
  };
}
