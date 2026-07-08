import { useEffect, useState, type ReactNode } from "react";
import {
  RequestFailedError,
  type HaltReason,
  type Job,
  type JobResult,
  type TestCase,
} from "../api/jobs";
import { useSymbolicTypes } from "../context/SymbolicTypeContext";
import { availableTypes, decode, type SymbolicType } from "../lib/decodeSymbolic";
import { useJob } from "../hooks/useJob";
import { clampPage } from "../lib/pagination";
import { classifyResultsError } from "../lib/resultsError";

type ResultsProps = {
  jobId: string | null;
  submitError: Error | null;
  maxTime: number;
  errorsFirst: boolean;
  onErrorsFirstChange: (value: boolean) => void;
};

export function Results({
  jobId,
  submitError,
  maxTime,
  errorsFirst,
  onErrorsFirstChange,
}: ResultsProps) {
  const { data: job, error: queryError } = useJob(jobId);

  const errorKind = classifyResultsError(submitError, queryError);
  if (errorKind === "expired") return <ExpiredState />;
  if (errorKind === "submit-rejected") {
    // classifier returns this only for a RequestFailedError, safe to narrow.
    return <SubmitRejectedState error={submitError as RequestFailedError} />;
  }
  if (errorKind === "unreachable") return <ConnectionErrorState />;
  if (jobId === null) return <EmptyState />;
  if (job === undefined) return <LoadingState />;

  return (
    <ResultsBody
      job={job}
      maxTime={maxTime}
      errorsFirst={errorsFirst}
      onErrorsFirstChange={onErrorsFirstChange}
    />
  );
}

function ResultsBody({
  job,
  maxTime,
  errorsFirst,
  onErrorsFirstChange,
}: {
  job: Job;
  maxTime: number;
  errorsFirst: boolean;
  onErrorsFirstChange: (value: boolean) => void;
}) {
  switch (job.status) {
    case "pending":
      return <PendingState />;
    case "running":
      return <RunningState createdAt={job.created_at} maxTime={maxTime} />;
    case "parsing":
      return <ParsingState />;
    case "done":
      if (job.result?.compile_error) {
        return <CompileErrorView error={job.result.compile_error} />;
      }
      return (
        <DoneView
          result={job.result!}
          errorsFirst={errorsFirst}
          onErrorsFirstChange={onErrorsFirstChange}
        />
      );
    case "failed":
      return <FailedState result={job.result ?? null} />;
  }
}

function CenterBlock({ children }: { children: ReactNode }) {
  return (
    <div className="h-full p-6 flex flex-col items-center justify-center text-center text-slate-600 dark:text-slate-400">
      {children}
    </div>
  );
}

function EmptyState() {
  return <CenterBlock>Click Run to execute KLEE on your code.</CenterBlock>;
}

function ExpiredState() {
  return <CenterBlock>Results for this run are no longer kept. Re-run to regenerate.</CenterBlock>;
}

function LoadingState() {
  return <CenterBlock>Loading...</CenterBlock>;
}

function ConnectionErrorState() {
  return <CenterBlock>Could not connect. Please check your connection and try again.</CenterBlock>;
}

function SubmitRejectedState({ error }: { error: RequestFailedError }) {
  return (
    <CenterBlock>
      <div>This run could not be started. Please try again.</div>
      {error.detail && (
        <div className="mt-2 text-xs font-mono text-slate-500 dark:text-slate-500">
          {error.detail}
        </div>
      )}
    </CenterBlock>
  );
}

function PendingState() {
  return <CenterBlock>Job queued, waiting for runner...</CenterBlock>;
}

function FailedState({ result }: { result: JobResult | null }) {
  return (
    <div className="h-full overflow-auto p-6">
      <h2 className="text-lg font-semibold text-rose-600 dark:text-rose-400 mb-3">Job failed</h2>
      {result?.messages && (
        <pre className="text-xs font-mono whitespace-pre-wrap p-3 rounded border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-900 text-slate-800 dark:text-slate-200">
          {result.messages}
        </pre>
      )}
    </div>
  );
}

function RunningState({ createdAt, maxTime }: { createdAt: string | undefined; maxTime: number }) {
  const elapsed = useElapsedSeconds(createdAt);
  const overrun = elapsed >= maxTime;
  return (
    <div className="h-full p-6 flex flex-col items-center justify-center gap-6 text-slate-700 dark:text-slate-300">
      <div className="flex items-center gap-2">
        <Spinner />
        <span>Running...</span>
      </div>
      <div className="text-center">
        <div
          className={`text-3xl font-semibold tabular-nums ${
            overrun ? "text-amber-600 dark:text-amber-400" : "text-slate-900 dark:text-slate-100"
          }`}
        >
          {formatClock(elapsed)}
        </div>
        <div className="text-xs text-slate-500 dark:text-slate-400">
          of {formatClock(maxTime)} limit
        </div>
      </div>
      {overrun && (
        <div className="max-w-xs text-center text-xs text-amber-600 dark:text-amber-400">
          Time limit reached. The job may be stopped soon and return incomplete results.
        </div>
      )}
      <div className="text-xs text-slate-500 dark:text-slate-500">
        Test cases will appear when the run finishes.
      </div>
    </div>
  );
}

function ParsingState() {
  return (
    <div className="h-full p-6 flex flex-col items-center justify-center gap-6 text-slate-700 dark:text-slate-300">
      <div className="flex flex-col items-center gap-1 text-center">
        <div className="flex items-center gap-2">
          <CheckIcon />
          <span>KLEE finished. Loading results...</span>
        </div>
        <div className="text-xs text-slate-500 dark:text-slate-500">
          This may take a few seconds depending on the number of test cases produced.
        </div>
      </div>
    </div>
  );
}

function CheckIcon() {
  return (
    <svg
      className="w-4 h-4 text-emerald-500"
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
      />
    </svg>
  );
}

function Spinner() {
  return (
    <div className="w-4 h-4 border-2 border-slate-300 dark:border-slate-600 border-t-[var(--klee-accent)] rounded-full animate-spin" />
  );
}

function CompileErrorView({ error }: { error: string }) {
  return (
    <div className="h-full overflow-auto p-6">
      <h2 className="text-lg font-semibold text-rose-600 dark:text-rose-400 mb-3">
        Compilation failed
      </h2>
      <pre className="text-xs font-mono whitespace-pre-wrap p-3 rounded border border-rose-200 dark:border-rose-900 bg-rose-50 dark:bg-rose-950 text-rose-800 dark:text-rose-200">
        {error}
      </pre>
    </div>
  );
}

const PAGE_SIZES = [25, 50, 75, 100] as const;

function DoneView({
  result,
  errorsFirst,
  onErrorsFirstChange,
}: {
  result: JobResult;
  errorsFirst: boolean;
  onErrorsFirstChange: (value: boolean) => void;
}) {
  const [tab, setTab] = useState<"tests" | "stats">("tests");
  const [pageSize, setPageSize] = useState<number>(PAGE_SIZES[0]);
  const [page, setPage] = useState(0);

  const errorCount = result.test_cases.filter((tc) => tc.error != null).length;
  const sortedCases = errorsFirst
    ? [...result.test_cases].sort((a, b) => (b.error != null ? 1 : 0) - (a.error != null ? 1 : 0))
    : result.test_cases;

  const total = sortedCases.length;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const currentPage = Math.min(page, pageCount - 1);
  const start = currentPage * pageSize;
  const pageItems = sortedCases.slice(start, start + pageSize);

  const handleErrorsFirstToggle = () => {
    onErrorsFirstChange(!errorsFirst);
    setPage(0);
  };

  return (
    <div className="h-full flex flex-col">
      <TabBar tab={tab} onTabChange={setTab} testCaseCount={total} />
      {result.halt_reason && <HaltBadge reason={result.halt_reason} />}
      <MessagesWarnings
        programOutput={result.program_output}
        messages={result.messages}
        warnings={result.warnings}
      />
      {tab === "tests" && total > 0 && (
        <PaginationControls
          page={currentPage}
          pageCount={pageCount}
          pageSize={pageSize}
          start={start}
          shown={pageItems.length}
          total={total}
          onPageChange={setPage}
          onPageSizeChange={(size) => {
            setPageSize(size);
            setPage(0);
          }}
          errorsFirst={errorsFirst}
          errorCount={errorCount}
          onToggleErrorsFirst={handleErrorsFirstToggle}
        />
      )}
      <div className="flex-1 overflow-auto p-4">
        {tab === "tests" ? (
          <TestCasesPanel testCases={pageItems} />
        ) : (
          <StatsPanel stats={result.stats} />
        )}
      </div>
    </div>
  );
}

function MessagesWarnings({
  programOutput,
  messages,
  warnings,
}: {
  programOutput: string;
  messages: string;
  warnings: string;
}) {
  if (!programOutput && !messages && !warnings) return null;
  return (
    <div className="shrink-0 px-4 py-2 space-y-2 border-b border-slate-200 dark:border-slate-700">
      {programOutput && <Collapsible title="Raw output (all paths)" content={programOutput} />}
      {messages && <Collapsible title="Messages" content={messages} />}
      {warnings && <Collapsible title="Warnings" content={warnings} />}
    </div>
  );
}

function PaginationControls({
  page,
  pageCount,
  pageSize,
  start,
  shown,
  total,
  onPageChange,
  onPageSizeChange,
  errorsFirst,
  errorCount,
  onToggleErrorsFirst,
}: {
  page: number;
  pageCount: number;
  pageSize: number;
  start: number;
  shown: number;
  total: number;
  onPageChange: (p: number) => void;
  onPageSizeChange: (s: number) => void;
  errorsFirst: boolean;
  errorCount: number;
  onToggleErrorsFirst: () => void;
}) {
  return (
    <div className="shrink-0 flex flex-wrap items-center justify-between gap-2 px-4 py-1.5 text-xs border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-600 dark:text-slate-400">
      <div className="flex items-center gap-1.5">
        <span>Per page</span>
        {PAGE_SIZES.map((size) => (
          <button
            key={size}
            type="button"
            onClick={() => onPageSizeChange(size)}
            className={`px-1.5 py-0.5 rounded ${
              size === pageSize
                ? "bg-[var(--klee-accent)] text-white"
                : "hover:text-slate-900 dark:hover:text-slate-100"
            }`}
          >
            {size}
          </button>
        ))}
        <span
          className={errorCount === 0 ? "ml-2 cursor-not-allowed" : "ml-2"}
          title={errorCount === 0 ? "KLEE reported no error cases in this run." : undefined}
        >
          <button
            type="button"
            disabled={errorCount === 0}
            onClick={onToggleErrorsFirst}
            className={`px-1.5 py-0.5 rounded disabled:pointer-events-none disabled:opacity-40 ${
              errorsFirst && errorCount > 0
                ? "bg-[var(--klee-accent)] text-white"
                : "hover:text-slate-900 dark:hover:text-slate-100"
            }`}
          >
            Errors first ({errorCount})
          </button>
        </span>
      </div>
      <div className="flex items-center gap-2 tabular-nums">
        <span>
          Showing {start + 1} to {start + shown} of {total}
        </span>
        <button
          type="button"
          disabled={page === 0}
          onClick={() => onPageChange(page - 1)}
          className="px-2 py-0.5 rounded border border-slate-200 dark:border-slate-700 disabled:opacity-40 enabled:hover:bg-slate-100 dark:enabled:hover:bg-slate-800"
        >
          Prev
        </button>
        <PageInput page={page} pageCount={pageCount} onPageChange={onPageChange} />
        <button
          type="button"
          disabled={page >= pageCount - 1}
          onClick={() => onPageChange(page + 1)}
          className="px-2 py-0.5 rounded border border-slate-200 dark:border-slate-700 disabled:opacity-40 enabled:hover:bg-slate-100 dark:enabled:hover:bg-slate-800"
        >
          Next
        </button>
      </div>
    </div>
  );
}

function PageInput({
  page,
  pageCount,
  onPageChange,
}: {
  page: number;
  pageCount: number;
  onPageChange: (p: number) => void;
}) {
  const commit = (el: HTMLInputElement) => {
    const next = clampPage(el.value, page + 1, pageCount);
    el.value = String(next);
    onPageChange(next - 1);
  };
  return (
    <span className="flex items-center gap-1">
      Page
      <input
        key={page}
        type="text"
        inputMode="numeric"
        aria-label="page number"
        defaultValue={page + 1}
        onKeyDown={(e) => {
          if (e.key === "Enter") e.currentTarget.blur();
        }}
        onBlur={(e) => commit(e.currentTarget)}
        className="w-10 text-center tabular-nums rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-[var(--klee-accent)]"
      />
      / {pageCount}
    </span>
  );
}

const HALT_BADGES: Record<HaltReason, { label: string; color: string }> = {
  completed: {
    label: "Explored all paths.",
    color: "bg-slate-50 dark:bg-slate-900 text-slate-600 dark:text-slate-400",
  },
  max_time: {
    label: "Stopped at max time. Some paths may be unexplored.",
    color: "bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300",
  },
  cancelled: {
    label: "Cancelled by user. Some paths may be unexplored.",
    color: "bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300",
  },
};

function HaltBadge({ reason }: { reason: HaltReason }) {
  const { label, color } = HALT_BADGES[reason];
  return (
    <div className={`px-4 py-1.5 text-xs border-b border-slate-200 dark:border-slate-700 ${color}`}>
      {label}
    </div>
  );
}

function TabBar({
  tab,
  onTabChange,
  testCaseCount,
}: {
  tab: "tests" | "stats";
  onTabChange: (t: "tests" | "stats") => void;
  testCaseCount: number;
}) {
  return (
    <div className="flex border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 shrink-0">
      <TabButton active={tab === "tests"} onClick={() => onTabChange("tests")}>
        Test cases ({testCaseCount})
      </TabButton>
      <TabButton active={tab === "stats"} onClick={() => onTabChange("stats")}>
        Stats
      </TabButton>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-4 py-2 text-sm border-b-2 -mb-px ${
        active
          ? "border-[var(--klee-accent)] text-slate-900 dark:text-slate-100"
          : "border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100"
      }`}
    >
      {children}
    </button>
  );
}

function TestCasesPanel({ testCases }: { testCases: TestCase[] }) {
  if (testCases.length === 0) {
    return <div className="text-sm text-slate-500">No test cases.</div>;
  }
  return (
    <div className="space-y-2">
      {testCases.map((tc) => (
        <TestCaseCard key={tc.name} testCase={tc} />
      ))}
    </div>
  );
}

function TestCaseCard({ testCase }: { testCase: TestCase }) {
  const { typeFor, setType } = useSymbolicTypes();
  return (
    <div className="rounded border border-slate-200 dark:border-slate-700 overflow-hidden">
      <div className="px-3 py-1.5 bg-slate-100 dark:bg-slate-900 text-sm font-mono text-slate-700 dark:text-slate-300">
        {testCase.name}
      </div>
      <div className="px-3 py-2 bg-white dark:bg-slate-950 space-y-1">
        {testCase.inputs.map((input) => {
          const width = input.bytes_hex.length / 2;
          const type = typeFor(input.name, width);
          return (
            <div key={input.name} className="font-mono text-xs flex items-center gap-2">
              <span className="text-slate-500">{input.name}</span>
              <span className="text-slate-400">=</span>
              <span className="flex-1 min-w-0 wrap-anywhere text-slate-900 dark:text-slate-100">
                {decode(input.bytes_hex, type)}
              </span>
              <select
                aria-label={`type for ${input.name}`}
                value={type}
                onChange={(e) => setType(input.name, e.target.value as SymbolicType)}
                className="shrink-0 rounded border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-1 py-0.5 text-slate-600 dark:text-slate-300"
              >
                {availableTypes(width).map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
          );
        })}
      </div>
      {testCase.program_output && (
        <details className="border-t border-slate-200 dark:border-slate-700">
          <summary className="px-3 py-1.5 cursor-pointer select-none text-xs text-slate-600 dark:text-slate-400">
            Output
          </summary>
          <pre className="px-3 py-2 text-xs font-mono whitespace-pre-wrap wrap-anywhere overflow-auto max-h-64 bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-200">
            {testCase.program_output}
          </pre>
        </details>
      )}
      {testCase.error && (
        <div className="px-3 py-2 text-xs font-mono whitespace-pre-wrap bg-rose-50 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border-t border-rose-200 dark:border-rose-900">
          {testCase.error}
        </div>
      )}
      {testCase.path_constraint && (
        <details className="border-t border-slate-200 dark:border-slate-700">
          <summary className="px-3 py-1.5 cursor-pointer select-none text-xs text-slate-600 dark:text-slate-400">
            Path constraint (KQuery)
          </summary>
          <pre className="px-3 py-2 text-xs font-mono whitespace-pre-wrap overflow-auto max-h-64 bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-200">
            {testCase.path_constraint}
          </pre>
        </details>
      )}
    </div>
  );
}

function StatsPanel({ stats }: { stats: Record<string, number> }) {
  const entries = Object.entries(stats);
  if (entries.length === 0) {
    return <div className="text-sm text-slate-500">No stats.</div>;
  }
  return (
    <div>
      {entries.map(([key, value]) => (
        <div
          key={key}
          className="font-mono text-xs flex justify-between py-1 border-b border-slate-100 dark:border-slate-800"
        >
          <span className="text-slate-600 dark:text-slate-400">{key}</span>
          <span className="tabular-nums text-slate-900 dark:text-slate-100">
            {value.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  );
}

function Collapsible({ title, content }: { title: string; content: string }) {
  const lineCount = content.replace(/\n$/, "").split("\n").length;
  return (
    <details className="rounded border border-slate-200 dark:border-slate-700">
      <summary className="px-3 py-1.5 cursor-pointer text-sm bg-slate-50 dark:bg-slate-900 select-none text-slate-700 dark:text-slate-300">
        {title}
        <span className="text-slate-400 dark:text-slate-500">{` · ${lineCount.toLocaleString()} ${lineCount === 1 ? "line" : "lines"}`}</span>
      </summary>
      <pre className="px-3 py-2 text-xs font-mono whitespace-pre-wrap wrap-anywhere overflow-auto bg-white dark:bg-slate-950 max-h-64 text-slate-800 dark:text-slate-200">
        {content}
      </pre>
    </details>
  );
}

function useElapsedSeconds(createdAtIso: string | undefined): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  if (!createdAtIso) return 0;
  return Math.max(0, Math.floor((now - new Date(createdAtIso).getTime()) / 1000));
}

function formatClock(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60);
  const s = Math.floor(totalSeconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
