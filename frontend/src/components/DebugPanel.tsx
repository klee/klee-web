import { useJob } from "../hooks/useJob"

// A read-only window on the raw job poll, gated on ?debug in HomePage. It surfaces
// the Stage 2 state the normal UI hides or only partly renders (status transitions,
// attempts, halt/failure reasons, poll cadence) without needing the browser devtools.
export function DebugPanel({ jobId }: { jobId: string | null }) {
  const { data: job, dataUpdatedAt, isFetching, isError } = useJob(jobId)

  return (
    <div className="fixed bottom-3 right-3 z-50 w-72 max-h-[60vh] overflow-auto rounded border border-amber-400 dark:border-amber-600 bg-white/95 dark:bg-slate-900/95 shadow-lg text-xs font-mono text-slate-800 dark:text-slate-200">
      <div className="px-3 py-1.5 border-b border-amber-300 dark:border-amber-700 bg-amber-100 dark:bg-amber-950 font-semibold flex items-center justify-between">
        <span>debug</span>
        <span className={isFetching ? "text-amber-600 dark:text-amber-400" : "text-slate-400"}>
          {isFetching ? "polling" : "idle"}
        </span>
      </div>
      <dl className="px-3 py-2 space-y-1">
        <Row k="jobId" v={jobId ?? "(none)"} />
        <Row k="status" v={job?.status ?? "(no job)"} />
        <Row k="attempts" v={job ? String(job.attempts) : "-"} />
        <Row k="halt_reason" v={job?.result?.halt_reason ?? "-"} />
        <Row k="failure_reason" v={job?.failure_reason ?? "-"} />
        <Row k="test_cases" v={job?.result ? String(job.result.test_cases.length) : "-"} />
        <Row k="updated" v={dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString() : "-"} />
        {isError && <Row k="error" v="poll failed" />}
      </dl>
    </div>
  )
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-slate-500 dark:text-slate-400">{k}</span>
      <span className="text-right break-all">{v}</span>
    </div>
  )
}
