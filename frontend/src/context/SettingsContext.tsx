import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

type Theme = "system" | "dark" | "light";
type ResolvedTheme = "dark" | "light";
type ResultsPosition = "right" | "below";
type Accent = "slate" | "blue" | "green" | "amber" | "red";

const ACCENTS: Record<Accent, string> = {
  slate: "#475569",
  blue: "#2563eb",
  green: "#16a34a",
  amber: "#d97706",
  red: "#dc2626",
};

type SettingsValue = {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  resultsPosition: ResultsPosition;
  accent: Accent;
  accents: Record<Accent, string>;
  fontSize: number;
  mainPanelSize: number;
  setTheme: (t: Theme) => void;
  setResultsPosition: (p: ResultsPosition) => void;
  setAccent: (a: Accent) => void;
  setFontSize: (n: number) => void;
  setMainPanelSize: (n: number) => void;
};

const SettingsContext = createContext<SettingsValue | null>(null);

const THEME_KEY = "klee.theme";
const RESULTS_POSITION_KEY = "klee.resultsPosition";
const ACCENT_KEY = "klee.accent";
const FONT_SIZE_KEY = "klee.fontSize";
const DEFAULT_FONT_SIZE = 14;
const MAIN_PANEL_SIZE_KEY = "klee.mainPanelSize";
const DEFAULT_MAIN_PANEL_SIZE = 50;

function readTheme(): Theme {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === "system" || stored === "dark" || stored === "light") return stored;
  return "system";
}

function readResultsPosition(): ResultsPosition {
  const stored = localStorage.getItem(RESULTS_POSITION_KEY);
  if (stored === "right" || stored === "below") return stored;
  return "right";
}

function readAccent(): Accent {
  const stored = localStorage.getItem(ACCENT_KEY);
  if (stored && stored in ACCENTS) return stored as Accent;
  return "slate";
}

function readFontSize(): number {
  const stored = localStorage.getItem(FONT_SIZE_KEY);
  if (stored) {
    const n = Number(stored);
    if (Number.isFinite(n) && n >= 10 && n <= 24) return n;
  }
  return DEFAULT_FONT_SIZE;
}

function readMainPanelSize(): number {
  const stored = localStorage.getItem(MAIN_PANEL_SIZE_KEY);
  if (stored) {
    const n = Number(stored);
    if (Number.isFinite(n) && n >= 20 && n <= 80) return n;
  }
  return DEFAULT_MAIN_PANEL_SIZE;
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(readTheme);
  const [resultsPosition, setResultsPosition] = useState<ResultsPosition>(readResultsPosition);
  const [accent, setAccent] = useState<Accent>(readAccent);
  const [fontSize, setFontSize] = useState<number>(readFontSize);
  const [mainPanelSize, setMainPanelSize] = useState<number>(readMainPanelSize);
  const [systemPrefersDark, setSystemPrefersDark] = useState<boolean>(
    () => window.matchMedia("(prefers-color-scheme: dark)").matches,
  );

  useEffect(() => {
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setSystemPrefersDark(mql.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  const resolvedTheme: ResolvedTheme =
    theme === "dark" ? "dark" : theme === "light" ? "light" : systemPrefersDark ? "dark" : "light";

  useEffect(() => {
    document.documentElement.classList.toggle("dark", resolvedTheme === "dark");
  }, [resolvedTheme]);

  useEffect(() => {
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem(RESULTS_POSITION_KEY, resultsPosition);
  }, [resultsPosition]);

  useEffect(() => {
    localStorage.setItem(ACCENT_KEY, accent);
    document.documentElement.style.setProperty("--klee-accent", ACCENTS[accent]);
  }, [accent]);

  useEffect(() => {
    localStorage.setItem(FONT_SIZE_KEY, String(fontSize));
  }, [fontSize]);

  useEffect(() => {
    localStorage.setItem(MAIN_PANEL_SIZE_KEY, String(mainPanelSize));
  }, [mainPanelSize]);

  return (
    <SettingsContext.Provider
      value={{
        theme,
        resolvedTheme,
        resultsPosition,
        accent,
        accents: ACCENTS,
        fontSize,
        mainPanelSize,
        setTheme,
        setResultsPosition,
        setAccent,
        setFontSize,
        setMainPanelSize,
      }}
    >
      {children}
    </SettingsContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (ctx === null) throw new Error("useSettings must be used within SettingsProvider");
  return ctx;
}
