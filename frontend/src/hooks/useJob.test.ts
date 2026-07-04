import { describe, expect, test } from "vitest"
import { JobNotFoundError } from "../api/jobs"
import { jobRefetchInterval, jobShouldRetry } from "./useJob"

describe("jobRefetchInterval", () => {
  test("stops for a dropped job (JobNotFoundError)", () => {
    expect(jobRefetchInterval(new JobNotFoundError("x"), undefined)).toBe(false)
  })

  test("stops once the job is terminal", () => {
    expect(jobRefetchInterval(null, "done")).toBe(false)
    expect(jobRefetchInterval(null, "failed")).toBe(false)
  })

  test("keeps polling while pending or running", () => {
    expect(jobRefetchInterval(null, undefined)).toBe(1000)
    expect(jobRefetchInterval(null, "running")).toBe(1000)
  })

  test("keeps polling through a transient error while the job is still live", () => {
    expect(jobRefetchInterval(new Error("blip"), "running")).toBe(1000)
  })
})

describe("jobShouldRetry", () => {
  test("never retries a dropped job", () => {
    expect(jobShouldRetry(0, new JobNotFoundError("x"))).toBe(false)
  })

  test("retries a transient error up to the limit", () => {
    expect(jobShouldRetry(0, new Error("blip"))).toBe(true)
    expect(jobShouldRetry(3, new Error("blip"))).toBe(false)
  })
})
