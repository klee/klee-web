import { useQuery } from "@tanstack/react-query";
import { BASE_URL } from "../api/client";

declare const KLEE_VERSION: string;
const POLL_INTERVAL_MS = 5000;

type StatusBarProps = {
  source: string;
};

type Connection = "connected" | "disconnected";

export function StatusBar({ source }: StatusBarProps) {
  const { data, isError } = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const response = await fetch(`${BASE_URL}/health`);
      if (!response.ok) throw new Error(`status ${response.status}`);
      return true;
    },
    refetchInterval: POLL_INTERVAL_MS,
    retry: false,
  });

  const connection: Connection = data === true && !isError ? "connected" : "disconnected";

  const bytes = new TextEncoder().encode(source).length;

  return (
    <div className="px-3 py-1 border-t border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-900 text-xs grid grid-cols-[1fr_auto_1fr] items-center text-slate-700 dark:text-slate-300">
      <div className="flex items-center gap-4">
        <ConnectionIndicator connection={connection} />
        <span>{bytes} bytes</span>
      </div>
      <span role="note" className="font-medium text-amber-700 dark:text-amber-300">
        Do not submit confidential source code.
      </span>
      <span className="justify-self-end">KLEE {KLEE_VERSION}</span>
    </div>
  );
}

function ConnectionIndicator({ connection }: { connection: Connection }) {
  const { dot, label } = {
    connected: { dot: "bg-emerald-500", label: "Connected" },
    disconnected: { dot: "bg-rose-500", label: "Disconnected" },
  }[connection];

  return (
    <span className="flex items-center gap-2">
      <span className={`inline-block w-2 h-2 rounded-full ${dot}`} />
      <span>{label}</span>
    </span>
  );
}
