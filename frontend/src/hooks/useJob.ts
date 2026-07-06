import { useQuery } from "@tanstack/react-query";
import { getJob, JobNotFoundError, type Job, type JobStatus } from "../api/jobs";

const POLL_INTERVAL_MS = 1000;
const MAX_RETRIES = 3;

// A dropped job (404 -> JobNotFoundError) is terminal: stop polling and do not
// retry it. Otherwise React Query keeps refetching and retrying a job the backend
// will never return, and the expired state flickers between loading and error.
export function jobRefetchInterval(error: unknown, status: JobStatus | undefined): number | false {
  if (error instanceof JobNotFoundError) return false;
  if (status === "done" || status === "failed") return false;
  return POLL_INTERVAL_MS;
}

export function jobShouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof JobNotFoundError) return false;
  return failureCount < MAX_RETRIES;
}

export function useJob(jobId: string | null) {
  return useQuery<Job>({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId!),
    enabled: jobId !== null,
    retry: jobShouldRetry,
    refetchInterval: (query) => jobRefetchInterval(query.state.error, query.state.data?.status),
  });
}
