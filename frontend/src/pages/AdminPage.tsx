import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getTelemetry, getUsageStats, setWorkerCapacity, type WorkerTelemetry } from "../api/admin";
import { KleeLogo } from "../components/KleeLogo";

const POLL_INTERVAL_MS = 5000;

type CapacityChange = {
  workerName: string;
  maximum: number;
};

export function AdminPage() {
  const queryClient = useQueryClient();
  const telemetry = useQuery({
    queryKey: ["admin", "telemetry"],
    queryFn: getTelemetry,
    refetchInterval: POLL_INTERVAL_MS,
  });
  const stats = useQuery({
    queryKey: ["admin", "stats"],
    queryFn: getUsageStats,
    refetchInterval: POLL_INTERVAL_MS,
  });
  const capacity = useMutation({
    mutationFn: ({ workerName, maximum }: CapacityChange) => setWorkerCapacity(workerName, maximum),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "telemetry"] }),
  });

  const workers = telemetry.data?.workers ?? [];
  const currentProcesses = workers.reduce((total, worker) => total + worker.concurrency, 0);
  const activeJobs = workers.reduce((total, worker) => total + worker.active, 0);
  const reservedJobs = workers.reduce((total, worker) => total + worker.reserved, 0);
  const waitingJobs = (telemetry.data?.queue?.depth ?? 0) + reservedJobs;
  const submissions = stats.data
    ? Object.values(stats.data.outcomes).reduce((total, count) => total + count, 0)
    : 0;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <header className="border-b border-slate-200 bg-slate-100 dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto flex max-w-6xl items-end justify-between px-5 py-5">
          <div>
            <div className="flex items-center gap-3">
              <KleeLogo />
              <span className="border-l border-slate-300 pl-3 text-sm font-medium text-slate-600 dark:border-slate-700 dark:text-slate-300">
                Administration
              </span>
            </div>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight">Fleet operations</h1>
          </div>
          <Link
            to="/"
            className="text-sm font-medium text-slate-600 hover:text-slate-950 dark:text-slate-300 dark:hover:text-white"
          >
            Workspace
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-8 px-5 py-7">
        {(telemetry.isPending || stats.isPending) && (
          <p className="text-sm text-slate-500 dark:text-slate-400">Loading operations data...</p>
        )}
        {(telemetry.isError || stats.isError) && (
          <p className="rounded border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300">
            Some operations data could not be loaded. The page will keep retrying.
          </p>
        )}

        <section aria-label="Fleet summary" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Waiting jobs" value={`${waitingJobs} waiting`} />
          <Metric label="Active jobs" value={`${activeJobs} active`} />
          <Metric label="Current capacity" value={`${currentProcesses} processes`} />
          <Metric
            label="Deployment limit"
            value={`${telemetry.data?.max_worker_concurrency ?? 0} per worker`}
          />
        </section>

        <section>
          <div className="mb-3 flex items-baseline justify-between gap-4">
            <h2 className="text-lg font-semibold">Workers</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">Live, refreshed every 5s</p>
          </div>
          <div className="space-y-3">
            {workers.map((worker) => (
              <WorkerCard
                key={`${worker.name}:${worker.max_concurrency}`}
                worker={worker}
                deploymentMaximum={telemetry.data?.max_worker_concurrency ?? 1}
                pending={capacity.isPending && capacity.variables?.workerName === worker.name}
                onApply={(workerName, maximum) => capacity.mutate({ workerName, maximum })}
              />
            ))}
            {telemetry.data && workers.length === 0 && (
              <p className="rounded border border-amber-300 bg-amber-50 px-4 py-4 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200">
                No workers are responding.
              </p>
            )}
          </div>
          {capacity.isError && (
            <p className="mt-3 text-sm text-rose-600 dark:text-rose-400">
              The capacity change was rejected. Refresh the fleet state and try again.
            </p>
          )}
        </section>

        <section>
          <div className="mb-3 flex items-baseline justify-between gap-4">
            <h2 className="text-lg font-semibold">Usage</h2>
            <p className="text-sm font-medium tabular-nums text-slate-600 dark:text-slate-300">
              {submissions} submissions
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Cache hits" value={String(stats.data?.cache_hits ?? 0)} />
            <Metric
              label="Tests generated"
              value={(stats.data?.test_cases_generated ?? 0).toLocaleString()}
            />
            <Metric
              label="Instructions"
              value={(stats.data?.instructions_executed ?? 0).toLocaleString()}
            />
            {stats.data &&
              Object.entries(stats.data.outcomes).map(([outcome, count]) => (
                <Metric key={outcome} label={outcome.replaceAll("_", " ")} value={String(count)} />
              ))}
          </div>
        </section>
      </main>
    </div>
  );
}

function WorkerCard({
  worker,
  deploymentMaximum,
  pending,
  onApply,
}: {
  worker: WorkerTelemetry;
  deploymentMaximum: number;
  pending: boolean;
  onApply: (workerName: string, maximum: number) => void;
}) {
  const inputId = `capacity-${worker.name}`;

  return (
    <article className="rounded border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h3 className="font-mono text-sm font-semibold">{worker.name}</h3>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            {worker.concurrency} processes · {worker.active} active · {worker.reserved} reserved
          </p>
          <p className="mt-1 text-xs font-medium text-slate-700 dark:text-slate-300">
            Live maximum {worker.max_concurrency}
          </p>
        </div>
        <form
          className="grid gap-1.5"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            const maximum = Number(form.get("maximum"));
            if (Number.isInteger(maximum)) onApply(worker.name, maximum);
          }}
        >
          <label
            htmlFor={inputId}
            className="text-xs font-medium text-slate-600 dark:text-slate-400"
          >
            Maximum concurrency
          </label>
          <div className="flex items-center gap-2">
            <input
              id={inputId}
              name="maximum"
              type="number"
              aria-label={`Maximum concurrency for ${worker.name}`}
              min={1}
              max={deploymentMaximum}
              defaultValue={worker.max_concurrency}
              className="w-32 rounded border border-slate-300 bg-white px-3 py-2 text-right text-base tabular-nums text-slate-900 focus:outline-none focus:ring-1 focus:ring-[var(--klee-accent)] dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            />
            <button
              type="submit"
              disabled={pending}
              aria-label={`Apply ${worker.name} capacity`}
              className="rounded bg-[var(--klee-accent)] px-4 py-2 text-sm font-medium text-white hover:brightness-110 disabled:opacity-60"
            >
              {pending ? "Applying..." : "Apply"}
            </button>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            Allowed range: 1 to {deploymentMaximum}
          </p>
        </form>
      </div>
    </article>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-slate-200 bg-white px-4 py-3 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {label}
      </p>
      <p className="mt-1 text-xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}
