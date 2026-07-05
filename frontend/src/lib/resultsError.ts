import { JobNotFoundError, RequestFailedError } from "../api/jobs"

export type ResultsErrorKind = "expired" | "submit-rejected" | "unreachable" | null

// Distinguishes the three failure shapes the results panel renders differently:
// a restored job the server dropped (expired), a run the server refused
// (submit-rejected), and anything else, chiefly a network failure (unreachable).
export function classifyResultsError(
  submitError: unknown,
  queryError: unknown,
): ResultsErrorKind {
  if (queryError instanceof JobNotFoundError) return "expired"
  if (submitError instanceof RequestFailedError) return "submit-rejected"
  if (submitError || queryError) return "unreachable"
  return null
}
