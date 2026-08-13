import { useState, type KeyboardEvent } from "react";
import type { KleeFlags } from "../api/jobs";

type FlagSpec = {
  field: keyof KleeFlags;
  label: string;
  unit: string;
  min: number;
  max: number;
  default: number;
};

type BooleanFlagField = {
  [Field in keyof KleeFlags]-?: KleeFlags[Field] extends boolean ? Field : never;
}[keyof KleeFlags];

type FlagToggle = {
  field: BooleanFlagField;
  label: string;
  hint: string;
  default: boolean;
};

const TIME: FlagSpec = {
  field: "max_time",
  label: "time",
  unit: "s",
  min: 1,
  max: 600,
  default: 60,
};

const MEMORY: FlagSpec = {
  field: "max_memory",
  label: "memory",
  unit: "MB",
  min: 64,
  max: 2048,
  default: 512,
};

const ENABLE_REPLAY: FlagToggle = {
  field: "enable_replay",
  label: "replay",
  hint: "Per-path replay captures readable output for each generated test. If KLEE generates many tests, try turning replay off to save time.",
  default: true,
};

type FlagBarProps = {
  flags: KleeFlags;
  onFlagsChange: (next: KleeFlags) => void;
};

export function FlagBar({ flags, onFlagsChange }: FlagBarProps) {
  return (
    <div className="flex items-center gap-5">
      <FlagInput spec={TIME} flags={flags} onFlagsChange={onFlagsChange} />
      <FlagInput spec={MEMORY} flags={flags} onFlagsChange={onFlagsChange} />
      <QueryFormatSelect flags={flags} onFlagsChange={onFlagsChange} />
      <FlagToggle toggle={ENABLE_REPLAY} flags={flags} onFlagsChange={onFlagsChange} />
      <ExtraFlagsInput flags={flags} onFlagsChange={onFlagsChange} />
    </div>
  );
}

function ExtraFlagsInput({ flags, onFlagsChange }: FlagBarProps) {
  return (
    <div className="flex items-center gap-1.5 text-sm">
      <span className="text-slate-600 dark:text-slate-400">flags</span>
      <input
        type="text"
        value={flags.extra_flags ?? ""}
        onChange={(e) => onFlagsChange({ ...flags, extra_flags: e.target.value })}
        placeholder="--optimize --search=dfs"
        aria-label="extra flags"
        spellCheck={false}
        className="w-52 px-1.5 py-0.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-[var(--klee-accent)]"
      />
    </div>
  );
}

function QueryFormatSelect({ flags, onFlagsChange }: FlagBarProps) {
  return (
    <div className="flex items-center gap-1.5 text-sm">
      <span className="text-slate-600 dark:text-slate-400">path constraint</span>
      <select
        value={flags.query_format ?? "none"}
        onChange={(e) =>
          onFlagsChange({
            ...flags,
            query_format: e.target.value as KleeFlags["query_format"],
          })
        }
        aria-label="path constraint format"
        className="px-1.5 py-0.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 focus:outline-none focus:ring-1 focus:ring-[var(--klee-accent)]"
      >
        <option value="none">off</option>
        <option value="kquery">KQuery</option>
      </select>
    </div>
  );
}

type FlagInputProps = {
  spec: FlagSpec;
  flags: KleeFlags;
  onFlagsChange: (next: KleeFlags) => void;
};

function FlagInput({ spec, flags, onFlagsChange }: FlagInputProps) {
  const current = flags[spec.field] ?? spec.default;
  const [text, setText] = useState<string>(String(current));
  const validity = validate(text, spec);

  function handleChange(next: string) {
    setText(next);
    const v = validate(next, spec);
    if (v.kind === "valid") {
      onFlagsChange({ ...flags, [spec.field]: v.value });
    } else if (v.kind === "empty") {
      onFlagsChange({ ...flags, [spec.field]: spec.default });
    }
  }

  function handleBlur() {
    if (validity.kind === "invalid") {
      setText(String(flags[spec.field] ?? spec.default));
    } else if (validity.kind === "empty") {
      setText(String(spec.default));
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.currentTarget.blur();
    }
  }

  const borderClass =
    validity.kind === "invalid" ? "border-rose-500" : "border-slate-300 dark:border-slate-700";

  return (
    <div className="relative flex items-center gap-1.5 text-sm">
      <span className="text-slate-600 dark:text-slate-400">{spec.label}</span>
      <input
        type="text"
        inputMode="numeric"
        value={text}
        onChange={(e) => handleChange(e.target.value)}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        aria-label={spec.label}
        className={`w-14 px-1.5 py-0.5 rounded border bg-white dark:bg-slate-950 text-right tabular-nums focus:outline-none focus:ring-1 focus:ring-[var(--klee-accent)] ${borderClass}`}
      />
      <span className="text-slate-600 dark:text-slate-400">{spec.unit}</span>
      {validity.kind === "invalid" && (
        <div className="absolute top-full left-0 mt-1 px-2 py-1 rounded text-xs whitespace-nowrap z-10 border bg-white dark:bg-slate-900 border-rose-500 text-rose-600 dark:text-rose-400">
          Must be a whole number between {spec.min} and {spec.max} {spec.unit}
        </div>
      )}
    </div>
  );
}

type FlagToggleProps = {
  toggle: FlagToggle;
  flags: KleeFlags;
  onFlagsChange: (next: KleeFlags) => void;
};

function FlagToggle({ toggle, flags, onFlagsChange }: FlagToggleProps) {
  return (
    <label
      title={toggle.hint}
      className="flex cursor-pointer select-none items-center gap-1.5 text-sm text-slate-600 dark:text-slate-400"
    >
      <span>{toggle.label}</span>
      <input
        type="checkbox"
        checked={flags[toggle.field] ?? toggle.default}
        onChange={(event) => onFlagsChange({ ...flags, [toggle.field]: event.target.checked })}
        aria-label={toggle.label}
        className="size-4 accent-[var(--klee-accent)]"
      />
    </label>
  );
}

type Validity = { kind: "valid"; value: number } | { kind: "empty" } | { kind: "invalid" };

function validate(text: string, spec: FlagSpec): Validity {
  const trimmed = text.trim();
  if (trimmed === "") return { kind: "empty" };
  const n = Number(trimmed);
  if (!Number.isInteger(n)) return { kind: "invalid" };
  if (n < spec.min || n > spec.max) return { kind: "invalid" };
  return { kind: "valid", value: n };
}
