import type { KleeFlags } from "../api/jobs";

export type HistoryStatus = "completed" | "max_time" | "cancelled" | "failed" | "compile_error";

export type HistoryEntry = {
  jobId: string;
  code: string;
  flags: KleeFlags;
  createdAt: number;
  status?: HistoryStatus;
};

export const MAX_ENTRIES = 50;
const KEY = "klee.history";

function isEntry(x: unknown): x is HistoryEntry {
  const e = x as HistoryEntry;
  return (
    typeof e === "object" &&
    e !== null &&
    typeof e.jobId === "string" &&
    typeof e.code === "string" &&
    typeof e.createdAt === "number" &&
    typeof e.flags === "object" &&
    e.flags !== null
  );
}

export function readHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isEntry).map((entry) => ({
      ...entry,
      flags: {
        ...entry.flags,
        enable_replay: entry.flags.enable_replay ?? true,
      },
    }));
  } catch {
    return [];
  }
}

function write(entries: HistoryEntry[]): HistoryEntry[] {
  localStorage.setItem(KEY, JSON.stringify(entries));
  return entries;
}

function sameFlags(a: KleeFlags, b: KleeFlags): boolean {
  return (
    a.max_time === b.max_time &&
    a.max_memory === b.max_memory &&
    a.enable_replay === b.enable_replay &&
    a.query_format === b.query_format
  );
}

export function addRun(entry: HistoryEntry): HistoryEntry[] {
  // Move-to-front with global uniqueness: an identical run (same code and flags)
  // anywhere in the list is dropped, so the fresh run replaces it at the top
  // rather than leaving a stale duplicate deeper down.
  const rest = readHistory().filter(
    (e) => !(e.code === entry.code && sameFlags(e.flags, entry.flags)),
  );
  return write([entry, ...rest].slice(0, MAX_ENTRIES));
}

export function setStatus(jobId: string, status: HistoryStatus): HistoryEntry[] {
  return write(readHistory().map((e) => (e.jobId === jobId ? { ...e, status } : e)));
}

export function removeEntry(jobId: string): HistoryEntry[] {
  return write(readHistory().filter((e) => e.jobId !== jobId));
}

export function clearHistory(): HistoryEntry[] {
  return write([]);
}
