import { useSettings } from "../context/SettingsContext"

export function SettingsPopover() {
  const { theme, setTheme, resultsPosition, setResultsPosition, fontSize, setFontSize, accentColor, setAccentColor } = useSettings()

  return (
    <div
      aria-label="Settings"
      className="absolute top-full right-0 mt-2 z-20 w-64 p-3 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-lg text-slate-900 dark:text-slate-100"
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
      <div className="mb-3">
        <SectionLabel>Font size: {fontSize}px</SectionLabel>
        <input
          type="range"
          min={10}
          max={24}
          step={1}
          value={fontSize}
          onChange={(e) => setFontSize(Number(e.target.value))}
          className="w-full h-1.5 rounded appearance-none cursor-pointer bg-slate-200 dark:bg-slate-700 accent-[var(--klee-accent)]"
          aria-label="Editor font size"
        />
      </div>
      <div>
        <SectionLabel>Accent color</SectionLabel>
        <div className="flex items-center gap-2">
          {ACCENT_PRESETS.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setAccentColor(c)}
              aria-label={`Accent ${c}`}
              aria-pressed={accentColor === c}
              className={`w-6 h-6 rounded-full border-2 ${
                accentColor === c ? "border-slate-900 dark:border-white scale-110" : "border-transparent"
              }`}
              style={{ backgroundColor: c }}
            />
          ))}
          <label className="relative ml-1">
            <input
              type="color"
              value={accentColor}
              onChange={(e) => setAccentColor(e.target.value)}
              className="w-6 h-6 rounded cursor-pointer border-0 p-0"
              aria-label="Custom accent color"
            />
          </label>
        </div>
      </div>
    </div>
  )
}

const ACCENT_PRESETS = [
  "#475569", // slate (current default)
  "#6b7280", // gray
  "#ef4444", // red
  "#f97316", // orange
  "#eab308", // yellow
  "#22c55e", // green
  "#14b8a6", // teal
  "#3b82f6", // blue
  "#6366f1", // indigo
  "#a855f7", // purple
  "#ec4899", // pink
]

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-1.5">
      {children}
    </div>
  )
}

type SegmentedProps<T extends string> = {
  value: T
  options: { value: T; label: string }[]
  onChange: (v: T) => void
}

function Segmented<T extends string>({ value, options, onChange }: SegmentedProps<T>) {
  return (
    <div className="inline-flex rounded border border-slate-200 dark:border-slate-700 overflow-hidden">
      {options.map((opt) => {
        const active = opt.value === value
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
        )
      })}
    </div>
  )
}
