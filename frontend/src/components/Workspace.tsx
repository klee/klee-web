import { type ReactNode } from "react";
import { useSettings } from "../context/SettingsContext";

type WorkspaceProps = {
  topBar: ReactNode;
  sidebar?: ReactNode;
  main: ReactNode;
  results: ReactNode;
  statusBar: ReactNode;
};

export function Workspace({ topBar, sidebar, main, results, statusBar }: WorkspaceProps) {
  const { resultsPosition } = useSettings();
  const mainResultsDirection = resultsPosition === "right" ? "flex-row" : "flex-col";

  return (
    <div className="h-screen flex flex-col bg-white text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <div className="shrink-0">{topBar}</div>
      <div className="flex-1 min-h-0 flex flex-row">
        {sidebar && <div className="shrink-0">{sidebar}</div>}
        <div className={`flex-1 min-h-0 min-w-0 flex ${mainResultsDirection}`}>
          <div className="flex-1 min-h-0 min-w-0 overflow-auto">{main}</div>
          <div className="flex-1 min-h-0 min-w-0 overflow-auto">{results}</div>
        </div>
      </div>
      <div className="shrink-0">{statusBar}</div>
    </div>
  );
}
