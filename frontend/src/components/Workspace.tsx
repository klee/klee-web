import { type ReactNode } from "react";
import { Panel, Group, Separator } from "react-resizable-panels";
import { useSettings } from "../context/SettingsContext";

type WorkspaceProps = {
  topBar: ReactNode;
  sidebar?: ReactNode;
  main: ReactNode;
  results: ReactNode;
  statusBar: ReactNode;
};

export function Workspace({ topBar, sidebar, main, results, statusBar }: WorkspaceProps) {
  const { resultsPosition, mainPanelSize, setMainPanelSize } = useSettings();
  const mainResultsDirection = resultsPosition === "right" ? "horizontal" : "vertical";

  return (
    <div className="h-screen flex flex-col bg-white text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <div className="shrink-0">{topBar}</div>
      <div className="flex-1 min-h-0 flex flex-row">
        {sidebar && <div className="shrink-0">{sidebar}</div>}
        <Group
          onLayoutChanged={(l) =>
            setMainPanelSize(Math.round((l.main / (l.main + l.results)) * 100))
          }
          orientation={mainResultsDirection}
          className="flex-1 min-h-0"
        >
          <Panel id="main" defaultSize={mainPanelSize} minSize="20%" className="overflow-auto">
            {main}
          </Panel>
          <Separator
            className={`transition-all duration-150
                                   bg-slate-200 dark:bg-slate-700
                                   hover:bg-[var(--klee-accent)] dark:hover:bg-[var(--klee-accent)]
                                   ${
                                     resultsPosition === "right"
                                       ? "w-1 cursor-col-resize hover:w-[6px]"
                                       : "h-1 cursor-row-resize hover:h-[6px]"
                                   }`}
          />
          <Panel
            id="results"
            defaultSize={100 - mainPanelSize}
            minSize="20%"
            className="overflow-auto"
          >
            {results}
          </Panel>
        </Group>
      </div>
      <div className="shrink-0">{statusBar}</div>
    </div>
  );
}
