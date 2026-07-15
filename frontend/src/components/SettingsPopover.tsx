import { Link } from "react-router-dom";
import { useSettings } from "../context/SettingsContext";

const ACCENT_OPTIONS = [
  { value: "slate", label: "Slate" },
  { value: "blue", label: "Blue" },
  { value: "green", label: "Green" },
  { value: "amber", label: "Amber" },
  { value: "red", label: "Red" },
] as const;

export function SettingsPopover() {
  const {
    theme,
    setTheme,
    resultsPosition,
    setResultsPosition,
    accent,
    setAccent,
    accents,
    fontSize,
    setFontSize,
  } = useSettings();

  return (
    <div
      aria-label="Settings"
      className="absolute top-full right-0 mt-2 z-20 w-56 p-3 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-lg text-slate-900 dark:text-slate-100"
    >
      <div className="mb-3">
        <SectionLabel>Theme</SectionLabel>
        <Segmented
          value={theme}
          options={[
            { value: "system", label: "System" },
            { value: "light", label: "Light" },
            { value: "dark", label: "Dark" },
          ]}
          onChange={setTheme}
        />
      </div>
      <div className="mb-3">
        <SectionLabel>Accent</SectionLabel>
        <div className="flex gap-1.5 flex-wrap">
          {ACCENT_OPTIONS.map((opt) => {
            const active = accent === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                aria-label={opt.label}
                aria-pressed={active}
                title={opt.label}
                onClick={() => setAccent(opt.value)}
                className={`w-6 h-6 rounded-full border-2 transition-shadow ${
                  active
                    ? "border-slate-900 dark:border-slate-100 shadow-md"
                    : "border-transparent hover:shadow-sm"
                }`}
                style={{ backgroundColor: accents[opt.value] }}
              />
            );
          })}
        </div>
      </div>
      <div className="mb-3">
        <SectionLabel>Font size ({fontSize}px)</SectionLabel>
        <input
          type="range"
          min={10}
          max={24}
          value={fontSize}
          onChange={(e) => setFontSize(Number(e.target.value))}
          className="w-full accent-[var(--klee-accent)]"
        />
      </div>
      <div>
        <SectionLabel>Results position</SectionLabel>
        <Segmented
          value={resultsPosition}
          options={[
            { value: "right", label: "Right" },
            { value: "below", label: "Below" },
          ]}
          onChange={setResultsPosition}
        />
      </div>
      <div className="mt-3 border-t border-slate-200 pt-3 dark:border-slate-700">
        <Link
          to="/admin"
          target="_blank"
          rel="noopener"
          className="flex items-center justify-between rounded px-2 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          Administration
          <span aria-hidden="true">→</span>
        </Link>
      </div>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-1.5">
      {children}
    </div>
  );
}

type SegmentedProps<T extends string> = {
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
};

function Segmented<T extends string>({ value, options, onChange }: SegmentedProps<T>) {
  return (
    <div className="inline-flex rounded border border-slate-200 dark:border-slate-700 overflow-hidden">
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            aria-pressed={active}
            className={
              active
                ? "px-3 py-1 text-xs font-medium text-white bg-[var(--klee-accent)]"
                : "px-3 py-1 text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
            }
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
