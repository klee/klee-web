import { useEffect, useState } from "react";
import type { KleeFlags } from "../api/jobs";
import { Editor } from "../components/Editor";
import { Results } from "../components/Results";
import { Sidebar } from "../components/Sidebar";
import { StatusBar } from "../components/StatusBar";
import { TopBar } from "../components/TopBar";
import { Workspace } from "../components/Workspace";
import { SymbolicTypeProvider } from "../context/SymbolicTypeContext";
import { DEFAULT_EXAMPLE } from "../data/examples";
import { useCancelJob } from "../hooks/useCancelJob";
import { useHistory } from "../hooks/useHistory";
import { useJob } from "../hooks/useJob";
import { useSubmitJob } from "../hooks/useSubmitJob";
import type { HistoryEntry } from "../lib/history";

const DEFAULT_FLAGS: KleeFlags = {
  max_time: 60,
  max_memory: 512,
  enable_replay: true,
  query_format: "none",
  extra_flags: "",
  sym_stdin: null,
  sym_files: null,
  sym_args: null,
};

function initialState(entries: HistoryEntry[]) {
  const newest = entries[0];
  if (newest) return { source: newest.code, flags: newest.flags, jobId: newest.jobId };
  return { source: DEFAULT_EXAMPLE.code, flags: DEFAULT_FLAGS, jobId: null as string | null };
}

export function HomePage() {
  const { entries, addRun, setStatus, removeEntry, clear } = useHistory();
  const [init] = useState(() => initialState(entries));
  const [source, setSource] = useState(init.source);
  const [flags, setFlags] = useState<KleeFlags>(init.flags);
  const [jobId, setJobId] = useState<string | null>(init.jobId);
  const [errorsFirst, setErrorsFirst] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const submitMutation = useSubmitJob();
  const cancelMutation = useCancelJob();
  const job = useJob(jobId);

  const status = job.data?.status ?? null;
  const jobActive = status === "pending" || status === "running" || status === "parsing";

  // The running job's own max_time, taken from its history entry so the countdown clock
  // reflects the value it was submitted with, not a later edit to the editor's flags.
  const activeMaxTime = entries.find((e) => e.jobId === jobId)?.flags.max_time ?? flags.max_time;

  // Write the terminal outcome back onto the history entry so the list can show a
  // glyph. Derived during render so the effect depends on the derived value and
  // fires once when the job reaches a terminal state, not every render (which would
  // loop under StrictMode).
  const terminalStatus = job.data?.outcome ?? null;
  useEffect(() => {
    if (jobId && terminalStatus) setStatus(jobId, terminalStatus);
  }, [jobId, terminalStatus, setStatus]);

  const handleRun = () => {
    setCancelling(false);
    submitMutation.mutate(
      { source, flags },
      {
        onSuccess: (data) => {
          setJobId(data.job_id);
          addRun({ jobId: data.job_id, code: source, flags, createdAt: Date.now() });
        },
      },
    );
  };

  const handleCancel = () => {
    if (!jobId) return;
    cancelMutation.mutate(jobId, {
      onSuccess: (landed) => {
        if (landed) setCancelling(true);
      },
    });
  };

  const loadExample = (code: string) => {
    setCancelling(false);
    submitMutation.reset();
    setJobId(null);
    setSource(code);
  };

  const restoreRun = (entry: HistoryEntry) => {
    setCancelling(false);
    submitMutation.reset();
    setSource(entry.code);
    setFlags(entry.flags);
    setJobId(entry.jobId);
  };

  return (
    <Workspace
      topBar={
        <TopBar
          flags={flags}
          onFlagsChange={setFlags}
          onRun={handleRun}
          jobActive={jobActive}
          cancelling={cancelling}
          onCancel={handleCancel}
        />
      }
      sidebar={
        <Sidebar
          entries={entries}
          onLoadExample={loadExample}
          onRestore={restoreRun}
          onDelete={removeEntry}
          onClear={clear}
          collapsed={!sidebarOpen}
          onToggleCollapsed={() => setSidebarOpen((v) => !v)}
        />
      }
      main={<Editor value={source} onChange={setSource} />}
      results={
        <SymbolicTypeProvider>
          <Results
            jobId={jobId}
            submitError={submitMutation.error}
            maxTime={activeMaxTime}
            errorsFirst={errorsFirst}
            onErrorsFirstChange={setErrorsFirst}
          />
        </SymbolicTypeProvider>
      }
      statusBar={<StatusBar source={source} />}
    />
  );
}
