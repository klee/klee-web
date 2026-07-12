import { useQuery } from "@tanstack/react-query";
import { BASE_URL } from "../api/client";

const KLEE_VERSION = "v3.2";
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
    <div className="px-3 py-1 border-t border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-900 text-xs flex items-center gap-4 text-slate-700 dark:text-slate-300">
      <ConnectionIndicator connection={connection} />
      <span>{bytes} bytes</span>
      <span className="ml-auto">KLEE {KLEE_VERSION}</span>
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
