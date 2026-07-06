import { useCallback, useState } from "react";
import type { KleeFlags } from "../api/jobs";
import {
  addRun as addRunStore,
  clearHistory,
  readHistory,
  removeEntry as removeEntryStore,
  setStatus as setStatusStore,
  type HistoryEntry,
  type HistoryStatus,
} from "../lib/history";

type RunInput = { jobId: string; code: string; flags: KleeFlags; createdAt: number };

export function useHistory() {
  const [entries, setEntries] = useState<HistoryEntry[]>(readHistory);

  const addRun = useCallback((run: RunInput) => setEntries(addRunStore(run)), []);
  const setStatus = useCallback(
    (jobId: string, status: HistoryStatus) => setEntries(setStatusStore(jobId, status)),
    [],
  );
  const removeEntry = useCallback((jobId: string) => setEntries(removeEntryStore(jobId)), []);
  const clear = useCallback(() => setEntries(clearHistory()), []);

  return { entries, addRun, setStatus, removeEntry, clear };
}
