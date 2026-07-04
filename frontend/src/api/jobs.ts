import type { components } from "../types/api";
import { apiClient } from "./client";

export type HaltReason = components["schemas"]["HaltReason"];
export type Job = components["schemas"]["Job"];
export type JobCreated = components["schemas"]["JobCreated"];
export type JobRequest = components["schemas"]["JobRequest"];
export type JobResult = components["schemas"]["JobResult"];
export type JobStatus = components["schemas"]["JobStatus"];
export type KleeFlags = components["schemas"]["KleeFlags"];
export type TestCase = components["schemas"]["TestCase"];

export async function submitJob(req: JobRequest): Promise<JobCreated> {
  const { data, error } = await apiClient.POST("/jobs", { body: req });
  if (error) {
    throw new Error(`submitJob failed: ${JSON.stringify(error)}`);
  }
  return data;
}

export async function getJob(jobId: string): Promise<Job> {
  const { data, error } = await apiClient.GET("/jobs/{job_id}", {
    params: { path: { job_id: jobId } },
  });
  if (error) {
    throw new Error(`getJob(${jobId}) failed: ${JSON.stringify(error)}`);
  }
  return data;
}

// Returns true only when the cancel landed (202). A 409 means there was no live
// container to signal (still starting, or already finished): a no-op the caller
// clicks through, not an error.
export async function cancelJob(jobId: string): Promise<boolean> {
  const { response } = await apiClient.POST("/jobs/{job_id}/cancel", {
    params: { path: { job_id: jobId } },
  });
  return response.status === 202;
}

export async function getTestCases(
  jobId: string,
  offset: number = 0,
  limit: number = 25,
): Promise<{ test_cases: components["schemas"]["TestCase"][]; total: number }> {
  const { data, error } = await apiClient.GET(
    "/jobs/{job_id}/test-cases",
    {
      params: {
        path: { job_id: jobId },
        query: { offset, limit },
      },
    },
  );
  if (error) {
    throw new Error(`getTestCases(${jobId}) failed: ${JSON.stringify(error)}`);
  }
  return data;
}
