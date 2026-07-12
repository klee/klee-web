import type { HistoryStatus } from "./history";

const MAX_LABEL = 48;

// A user can name a run with a comment: `// title: my run`. Also accepts the
// block form `/* title: x */` and a header-star line ` * title: x`, any case.
const TITLE_RE = /^(?:\/\/+|\/\*+|\*+)\s*title\s*:\s*(.+?)\s*(?:\*\/\s*)?$/i;

function truncate(s: string): string {
  return s.length > MAX_LABEL ? s.slice(0, MAX_LABEL - 3) + "..." : s;
}

export function historyLabel(code: string): string {
  const lines = code.split("\n");

  for (const raw of lines) {
    const match = raw.trim().match(TITLE_RE);
    if (match && match[1].trim()) return truncate(match[1].trim());
  }

  // No title: show the first line that is not comment, preprocessor, a lone
  // brace, or the main() signature. Keep the first non-comment line as a
  // fallback so an all-boilerplate program still gets a label.
  let fallback = "";
  for (const raw of lines) {
    const line = raw.trim();
    if (line === "") continue;
    if (line.startsWith("//") || line.startsWith("/*") || line.startsWith("*")) continue;
    if (fallback === "") fallback = line;
    if (line.startsWith("#")) continue;
    if (line === "{" || line === "}") continue;
    if (/\bmain\s*\(/.test(line)) continue;
    return truncate(line);
  }
  return fallback === "" ? "(empty)" : truncate(fallback);
}

export function relativeTime(fromMs: number, nowMs: number): string {
  const s = Math.max(0, Math.round((nowMs - fromMs) / 1000));
  if (s < 10) return "just now";
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export function statusGlyph(status: HistoryStatus): { glyph: string; label: string } {
  switch (status) {
    case "completed":
      return { glyph: "✓", label: "Explored all paths" };
    case "max_time":
      return { glyph: "⏱", label: "Stopped at max time" };
    case "cancelled":
      return { glyph: "⊘", label: "Cancelled" };
    case "failed":
      return { glyph: "✗", label: "Failed" };
    case "compile_error":
      return { glyph: "!", label: "Compile error" };
  }
}
