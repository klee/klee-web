import { afterEach, describe, expect, test, vi } from "vitest"
import { apiClient } from "./client"
import { getJob, JobNotFoundError } from "./jobs"

afterEach(() => {
  vi.restoreAllMocks()
})

describe("getJob", () => {
  test("throws JobNotFoundError on a 404", async () => {
    vi.spyOn(apiClient, "GET").mockResolvedValue({
      data: undefined,
      error: { detail: "Job not found" },
      response: { status: 404 },
    } as never)
    await expect(getJob("missing")).rejects.toBeInstanceOf(JobNotFoundError)
  })

  test("throws a generic error on other failures", async () => {
    vi.spyOn(apiClient, "GET").mockResolvedValue({
      data: undefined,
      error: { detail: "boom" },
      response: { status: 500 },
    } as never)
    const err = await getJob("x").catch((e) => e)
    expect(err).toBeInstanceOf(Error)
    expect(err).not.toBeInstanceOf(JobNotFoundError)
  })
})
