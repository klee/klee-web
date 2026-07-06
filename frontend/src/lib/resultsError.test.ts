import { describe, expect, test } from "vitest";
import { JobNotFoundError, RequestFailedError } from "../api/jobs";
import { classifyResultsError } from "./resultsError";

describe("classifyResultsError", () => {
  test("no errors classifies as null", () => {
    expect(classifyResultsError(null, null)).toBe(null);
  });

  test("a query JobNotFoundError is expired", () => {
    expect(classifyResultsError(null, new JobNotFoundError("abc"))).toBe("expired");
  });

  test("a submit RequestFailedError is submit-rejected", () => {
    expect(classifyResultsError(new RequestFailedError(422), null)).toBe("submit-rejected");
  });

  test("a generic submit error is unreachable", () => {
    expect(classifyResultsError(new Error("Failed to fetch"), null)).toBe("unreachable");
  });

  test("a generic query error is unreachable", () => {
    expect(classifyResultsError(null, new Error("boom"))).toBe("unreachable");
  });

  test("expired wins over a concurrent submit error", () => {
    expect(classifyResultsError(new RequestFailedError(500), new JobNotFoundError("abc"))).toBe(
      "expired",
    );
  });
});
