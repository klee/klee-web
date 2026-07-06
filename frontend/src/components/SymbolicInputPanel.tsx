import { useRef, useState, type KeyboardEvent } from "react";
import type { KleeFlags } from "../api/jobs";

type Props = {
  flags: KleeFlags;
  onFlagsChange: (next: KleeFlags) => void;
};

type SymStdin = NonNullable<KleeFlags["sym_stdin"]>;
type SymFiles = NonNullable<KleeFlags["sym_files"]>;
type SymArgs = NonNullable<KleeFlags["sym_args"]>;

export function SymbolicInputPanel({ flags, onFlagsChange }: Props) {
  const active = [flags.sym_stdin, flags.sym_files, flags.sym_args].filter(Boolean).length;
  return (
    <details className="px-3 pb-2 text-sm">
      <summary className="cursor-pointer select-none text-slate-600 dark:text-slate-400">
        Symbolic input
        {active > 0 && (
          <span className="ml-1.5 text-xs text-[var(--klee-accent)]">· {active} active</span>
        )}
      </summary>
      <div className="mt-2 flex flex-wrap items-center gap-x-6 gap-y-2 pl-1">
        <StdinRow
          value={flags.sym_stdin ?? null}
          onChange={(v) => onFlagsChange({ ...flags, sym_stdin: v })}
        />
        <FilesRow
          value={flags.sym_files ?? null}
          onChange={(v) => onFlagsChange({ ...flags, sym_files: v })}
        />
        <ArgsRow
          value={flags.sym_args ?? null}
          onChange={(v) => onFlagsChange({ ...flags, sym_args: v })}
        />
      </div>
    </details>
  );
}

function StdinRow({
  value,
  onChange,
}: {
  value: SymStdin | null;
  onChange: (v: SymStdin | null) => void;
}) {
  return (
    <div className="flex items-center gap-3">
      <Toggle
        label="stdin"
        enabled={value !== null}
        onToggle={(on) => onChange(on ? { size: 8 } : null)}
      />
      {value && (
        <NumField
          label="bytes"
          name="stdin bytes"
          value={value.size}
          min={1}
          max={256}
          onChange={(n) => onChange({ size: n })}
        />
      )}
    </div>
  );
}

function FilesRow({
  value,
  onChange,
}: {
  value: SymFiles | null;
  onChange: (v: SymFiles | null) => void;
}) {
  return (
    <div className="flex items-center gap-3">
      <Toggle
        label="files"
        enabled={value !== null}
        onToggle={(on) => onChange(on ? { count: 2, size: 8 } : null)}
      />
      {value && (
        <>
          <NumField
            label="count"
            name="files count"
            value={value.count}
            min={1}
            max={10}
            onChange={(n) => onChange({ ...value, count: n })}
          />
          <NumField
            label="bytes"
            name="files bytes"
            value={value.size}
            min={1}
            max={256}
            onChange={(n) => onChange({ ...value, size: n })}
          />
        </>
      )}
    </div>
  );
}

function ArgsRow({
  value,
  onChange,
}: {
  value: SymArgs | null;
  onChange: (v: SymArgs | null) => void;
}) {
  return (
    <div className="flex items-center gap-3">
      <Toggle
        label="args"
        enabled={value !== null}
        onToggle={(on) => onChange(on ? { count_min: 1, count_max: 3, length: 4 } : null)}
      />
      {value && (
        <>
          <NumField
            label="min"
            name="args min"
            value={value.count_min}
            min={0}
            max={10}
            onChange={(n) => onChange({ ...value, count_min: n })}
          />
          <NumField
            label="max"
            name="args max"
            value={value.count_max}
            min={1}
            max={10}
            onChange={(n) => onChange({ ...value, count_max: n })}
          />
          <NumField
            label="length"
            name="args length"
            value={value.length}
            min={1}
            max={100}
            onChange={(n) => onChange({ ...value, length: n })}
          />
        </>
      )}
    </div>
  );
}

function Toggle({
  label,
  enabled,
  onToggle,
}: {
  label: string;
  enabled: boolean;
  onToggle: (on: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-1.5 w-14 cursor-pointer select-none text-slate-700 dark:text-slate-300">
      <input
        type="checkbox"
        checked={enabled}
        onChange={(e) => onToggle(e.target.checked)}
        className="accent-[var(--klee-accent)]"
      />
      {label}
    </label>
  );
}

type NumFieldProps = {
  label: string;
  name: string;
  value: number;
  min: number;
  max: number;
  onChange: (n: number) => void;
};

function NumField({ label, name, value, min, max, onChange }: NumFieldProps) {
  const [text, setText] = useState(String(value));
  const editStart = useRef(value);
  const validity = numValidity(text, min, max);

  function handleFocus() {
    editStart.current = value;
  }

  function handleChange(next: string) {
    setText(next);
    const v = numValidity(next, min, max);
    if (v.kind === "valid") onChange(v.value);
  }

  function handleBlur() {
    if (validity.kind === "valid") return;
    // Out of range or empty: roll back to the number that was there when editing
    // began, undoing any in-range partial (e.g. "30" typed on the way to "300").
    setText(String(editStart.current));
    if (value !== editStart.current) onChange(editStart.current);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") e.currentTarget.blur();
  }

  const invalid = validity.kind === "invalid";

  return (
    <label className="flex items-center gap-1 text-slate-600 dark:text-slate-400">
      {label}
      <input
        type="text"
        inputMode="numeric"
        value={text}
        onFocus={handleFocus}
        onChange={(e) => handleChange(e.target.value)}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        aria-label={name}
        className={`w-12 px-1.5 py-0.5 rounded border bg-white dark:bg-slate-950 text-right tabular-nums text-xs focus:outline-none focus:ring-1 focus:ring-[var(--klee-accent)] ${
          invalid ? "border-rose-500" : "border-slate-300 dark:border-slate-700"
        }`}
      />
    </label>
  );
}

type NumValidity = { kind: "valid"; value: number } | { kind: "empty" } | { kind: "invalid" };

function numValidity(text: string, min: number, max: number): NumValidity {
  const trimmed = text.trim();
  if (trimmed === "") return { kind: "empty" };
  const n = Number(trimmed);
  if (!Number.isInteger(n)) return { kind: "invalid" };
  if (n < min || n > max) return { kind: "invalid" };
  return { kind: "valid", value: n };
}
