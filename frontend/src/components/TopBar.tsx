import { useEffect, useRef, useState } from "react";
import type { KleeFlags } from "../api/jobs";
import { FlagBar } from "./FlagBar";
import { KleeLogo } from "./KleeLogo";
import { SettingsPopover } from "./SettingsPopover";
import { SymbolicInputPanel } from "./SymbolicInputPanel";

type TopBarProps = {
  flags: KleeFlags;
  onFlagsChange: (next: KleeFlags) => void;
  onRun: () => void;
  jobActive: boolean;
  cancelling: boolean;
  onCancel: () => void;
};

export function TopBar({
  flags,
  onFlagsChange,
  onRun,
  jobActive,
  cancelling,
  onCancel,
}: TopBarProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const settingsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!settingsOpen) return;
    const onPointerDown = (e: PointerEvent) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) {
        setSettingsOpen(false);
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSettingsOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [settingsOpen]);

  return (
    <div className="border-b border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-900 text-slate-900 dark:text-slate-100">
      <div className="px-3 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <KleeLogo />
          <FlagBar flags={flags} onFlagsChange={onFlagsChange} />
        </div>
        <div className="flex items-center gap-2">
          {jobActive ? (
            <button
              type="button"
              onClick={onCancel}
              disabled={cancelling}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded text-sm font-medium text-white bg-rose-600 hover:brightness-110 active:brightness-95 disabled:opacity-60 disabled:cursor-default"
            >
              <StopIcon />
              {cancelling ? "Cancelling..." : "Cancel"}
            </button>
          ) : (
            <button
              type="button"
              onClick={onRun}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded text-sm font-medium text-white bg-[var(--klee-accent)] hover:brightness-110 active:brightness-95"
            >
              <PlayIcon />
              Run
            </button>
          )}
          <div ref={settingsRef} className="relative">
            <button
              type="button"
              onClick={() => setSettingsOpen((v) => !v)}
              aria-label="Settings"
              aria-expanded={settingsOpen}
              className="p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-800"
            >
              <CogIcon />
            </button>
            {settingsOpen && <SettingsPopover />}
          </div>
        </div>
      </div>
      <SymbolicInputPanel flags={flags} onFlagsChange={onFlagsChange} />
    </div>
  );
}

function PlayIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor" aria-hidden="true">
      <path d="M2 1 L9 5 L2 9 Z" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor" aria-hidden="true">
      <rect x="1.5" y="1.5" width="7" height="7" rx="1" />
    </svg>
  );
}

function CogIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}
