import { useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { getJob, JobNotFoundError, type Job, type JobStatus } from "../api/jobs";

const POLL_INTERVAL_MS = 1000;
const MAX_RETRIES = 3;
const CANCEL_ENRICH_GRACE_MS = 15_000;

// A dropped job (404 -> JobNotFoundError) is terminal: stop polling and do not
// retry it. Otherwise React Query keeps refetching and retrying a job the backend
// will never return, and the expired state flickers between loading and error.
export function jobRefetchInterval(error: unknown, status: JobStatus | undefined): number | false {
  if (error instanceof JobNotFoundError) return false;
  if (status === "done" || status === "failed") return false;
  return POLL_INTERVAL_MS;
}

// The empty result a cancel eager-flips to, before the executor enriches it with partials.
export function isAwaitingCancelPartials(job: Job | undefined): boolean {
  if (job?.status !== "done" || job.result == null) return false;
  return job.result.halt_reason === "cancelled" && job.result.test_cases.length === 0;
}

export function jobShouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof JobNotFoundError) return false;
  return failureCount < MAX_RETRIES;
}

export function useJob(jobId: string | null) {
  const enrichDeadline = useRef<number | null>(null);
  return useQuery<Job>({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId!),
    enabled: jobId !== null,
    retry: jobShouldRetry,
    refetchInterval: (query) => {
      const base = jobRefetchInterval(query.state.error, query.state.data?.status);
      if (base !== false) {
        enrichDeadline.current = null;
        return base;
      }
      if (!isAwaitingCancelPartials(query.state.data)) return false;
      const now = Date.now();
      if (enrichDeadline.current === null) enrichDeadline.current = now + CANCEL_ENRICH_GRACE_MS;
      return now < enrichDeadline.current ? POLL_INTERVAL_MS : false;
    },
  });
}
