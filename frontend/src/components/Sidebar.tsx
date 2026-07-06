import { useEffect, useState } from "react";
import { EXAMPLES } from "../data/examples";
import type { HistoryEntry } from "../lib/history";
import { historyLabel, relativeTime, statusGlyph } from "../lib/historyView";

type SidebarProps = {
  entries: HistoryEntry[];
  onLoadExample: (code: string) => void;
  onRestore: (entry: HistoryEntry) => void;
  onDelete: (jobId: string) => void;
  onClear: () => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
};

type Tab = "examples" | "history";

export function Sidebar({
  entries,
  onLoadExample,
  onRestore,
  onDelete,
  onClear,
  collapsed,
  onToggleCollapsed,
}: SidebarProps) {
  const [tab, setTab] = useState<Tab>("examples");

  if (collapsed) {
    return (
      <div className="h-full w-10 border-r border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-900 flex flex-col items-center pt-3">
        <button
          type="button"
          onClick={onToggleCollapsed}
          aria-label="Expand sidebar"
          className="p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-800"
        >
          »
        </button>
      </div>
    );
  }

  return (
    <div className="h-full w-56 border-r border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-900 flex flex-col text-sm text-slate-800 dark:text-slate-200">
      <div className="flex items-center justify-between px-2 py-2 border-b border-slate-200 dark:border-slate-800">
        <div className="flex gap-1">
          <TabButton
            label="Examples"
            active={tab === "examples"}
            onClick={() => setTab("examples")}
          />
          <TabButton label="History" active={tab === "history"} onClick={() => setTab("history")} />
        </div>
        <button
          type="button"
          onClick={onToggleCollapsed}
          aria-label="Collapse sidebar"
          className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800"
        >
          «
        </button>
      </div>

      <div className="flex-1 min-h-0 overflow-auto">
        {tab === "examples" ? (
          <ul className="py-1">
            {EXAMPLES.map((ex) => (
              <li key={ex.id}>
                <button
                  type="button"
                  onClick={() => onLoadExample(ex.code)}
                  className="w-full flex items-center justify-between gap-2 px-3 py-1.5 text-left hover:bg-slate-200 dark:hover:bg-slate-800"
                >
                  <span className="truncate">{ex.label}</span>
                  <span className="shrink-0 text-xs text-slate-500 dark:text-slate-400">
                    {ex.tag}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <HistoryList
            entries={entries}
            onRestore={onRestore}
            onDelete={onDelete}
            onClear={onClear}
          />
        )}
      </div>
      <HistoryHint />
    </div>
  );
}

function TabButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-2 py-1 rounded text-xs font-medium ${
        active
          ? "bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
          : "text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200"
      }`}
    >
      {label}
    </button>
  );
}

function HistoryList({
  entries,
  onRestore,
  onDelete,
  onClear,
}: Pick<SidebarProps, "entries" | "onRestore" | "onDelete" | "onClear">) {
  const now = useNow();
  if (entries.length === 0) {
    return (
      <div className="px-3 py-6 text-xs text-slate-500 dark:text-slate-400">
        No runs yet. Hit Run to start your history.
      </div>
    );
  }
  return (
    <div>
      <div className="flex justify-end px-2 py-1">
        <button
          type="button"
          onClick={onClear}
          className="text-xs text-slate-500 dark:text-slate-400 hover:text-rose-600 dark:hover:text-rose-400"
        >
          Clear
        </button>
      </div>
      <ul>
        {entries.map((e) => {
          const badge = e.status ? statusGlyph(e.status) : null;
          return (
            <li key={e.jobId} className="group flex items-center">
              <button
                type="button"
                data-testid="history-entry"
                onClick={() => onRestore(e)}
                className="flex-1 min-w-0 flex items-center gap-2 px-3 py-1.5 text-left hover:bg-slate-200 dark:hover:bg-slate-800"
              >
                <span className="w-3 shrink-0 text-center" title={badge?.label ?? ""}>
                  {badge?.glyph ?? ""}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-mono text-xs">{historyLabel(e.code)}</span>
                  <span className="block text-[11px] text-slate-500 dark:text-slate-400">
                    {relativeTime(e.createdAt, now)}
                  </span>
                </span>
              </button>
              <button
                type="button"
                onClick={() => onDelete(e.jobId)}
                aria-label="Delete run"
                className="px-2 opacity-0 group-hover:opacity-100 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400"
              >
                ×
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function HistoryHint() {
  return (
    <div className="border-t border-slate-200 dark:border-slate-800 px-3 py-2 text-[11px] leading-snug text-slate-500 dark:text-slate-400">
      Tip: start a line with{" "}
      <code className="rounded bg-slate-200 px-1 py-0.5 font-mono text-slate-700 dark:bg-slate-800 dark:text-slate-200">
        // title:
      </code>{" "}
      to name a run in your history.
    </div>
  );
}

function useNow(): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(id);
  }, []);
  return now;
}
