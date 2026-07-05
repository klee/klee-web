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
  const { data, error, response } = await apiClient.POST("/jobs", { body: req });
  if (error) {
    throw new RequestFailedError(response.status, requestDetail(error));
  }
  return data;
}

export class JobNotFoundError extends Error {
  constructor(jobId: string) {
    super(`job ${jobId} not found`);
    this.name = "JobNotFoundError";
  }
}

// The server was reached but refused the request (validation, rate limit, 5xx).
// Distinct from a network failure, which rejects before we get a response.
export class RequestFailedError extends Error {
  readonly status: number;
  readonly detail?: string;
  constructor(status: number, detail?: string) {
    super(`request failed (${status})`);
    this.name = "RequestFailedError";
    this.status = status;
    this.detail = detail;
  }
}

function requestDetail(body: unknown): string | undefined {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return undefined;
}

export async function getJob(jobId: string): Promise<Job> {
  const { data, error, response } = await apiClient.GET("/jobs/{job_id}", {
    params: { path: { job_id: jobId } },
  });
  // A restored history entry can point at a job the backend has dropped once its store TTL lapses.
  // Surface it distinctly so the UI shows "expired", not "backend not connected".
  if (response.status === 404) {
    throw new JobNotFoundError(jobId);
  }
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
