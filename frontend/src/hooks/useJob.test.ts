import { describe, expect, test } from "vitest";
import { JobNotFoundError, type Job } from "../api/jobs";
import { isAwaitingCancelPartials, jobRefetchInterval, jobShouldRetry } from "./useJob";

describe("jobRefetchInterval", () => {
  test("stops for a dropped job (JobNotFoundError)", () => {
    expect(jobRefetchInterval(new JobNotFoundError("x"), undefined)).toBe(false);
  });

  test("stops once the job is terminal", () => {
    expect(jobRefetchInterval(null, "done")).toBe(false);
    expect(jobRefetchInterval(null, "failed")).toBe(false);
  });

  test("keeps polling while pending or running", () => {
    expect(jobRefetchInterval(null, undefined)).toBe(1000);
    expect(jobRefetchInterval(null, "running")).toBe(1000);
  });

  test("keeps polling through a transient error while the job is still live", () => {
    expect(jobRefetchInterval(new Error("blip"), "running")).toBe(1000);
  });
});

describe("jobShouldRetry", () => {
  test("never retries a dropped job", () => {
    expect(jobShouldRetry(0, new JobNotFoundError("x"))).toBe(false);
  });

  test("retries a transient error up to the limit", () => {
    expect(jobShouldRetry(0, new Error("blip"))).toBe(true);
    expect(jobShouldRetry(3, new Error("blip"))).toBe(false);
  });
});

describe("isAwaitingCancelPartials", () => {
  const cancelledEmpty: Job = {
    status: "done",
    outcome: "cancelled",
    result: {
      test_cases: [],
      messages: "",
      warnings: "",
      stats: {},
      program_output: "",
      halt_reason: "cancelled",
      states_culled_for_memory: 0,
    },
  };

  test("true for the empty eager-flip cancel", () => {
    expect(isAwaitingCancelPartials(cancelledEmpty)).toBe(true);
  });

  test("false once partials arrive", () => {
    expect(
      isAwaitingCancelPartials({
        ...cancelledEmpty,
        result: { ...cancelledEmpty.result!, test_cases: [{ name: "t", inputs: [] }] },
      }),
    ).toBe(false);
  });

  test("false for a completed run with no tests", () => {
    expect(
      isAwaitingCancelPartials({
        ...cancelledEmpty,
        result: { ...cancelledEmpty.result!, halt_reason: "completed" },
      }),
    ).toBe(false);
  });

  test("false while still running", () => {
    expect(isAwaitingCancelPartials({ status: "running", outcome: null, result: null })).toBe(
      false,
    );
  });

  test("false for no job", () => {
    expect(isAwaitingCancelPartials(undefined)).toBe(false);
  });
});
