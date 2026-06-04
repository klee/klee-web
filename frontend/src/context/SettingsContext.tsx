import { createContext, useContext, useEffect, useState, type ReactNode } from "react"

type Theme = "system" | "dark" | "light"
type ResolvedTheme = "dark" | "light"
type ResultsPosition = "right" | "below"
type Accent = "slate" | "blue" | "green" | "amber" | "red"

const ACCENTS: Record<Accent, string> = {
  slate: "#475569",
  blue: "#2563eb",
  green: "#16a34a",
  amber: "#d97706",
  red: "#dc2626",
}

type SettingsValue = {
  theme: Theme
  resolvedTheme: ResolvedTheme
  resultsPosition: ResultsPosition
  accent: Accent
  accents: Record<Accent, string>
  setTheme: (t: Theme) => void
  setResultsPosition: (p: ResultsPosition) => void
  setAccent: (a: Accent) => void
}

const SettingsContext = createContext<SettingsValue | null>(null)

const THEME_KEY = "klee.theme"
const RESULTS_POSITION_KEY = "klee.resultsPosition"
const ACCENT_KEY = "klee.accent"

function readTheme(): Theme {
  const stored = localStorage.getItem(THEME_KEY)
  if (stored === "system" || stored === "dark" || stored === "light") return stored
  return "system"
}

function readResultsPosition(): ResultsPosition {
  const stored = localStorage.getItem(RESULTS_POSITION_KEY)
  if (stored === "right" || stored === "below") return stored
  return "right"
}

function readAccent(): Accent {
  const stored = localStorage.getItem(ACCENT_KEY)
  if (stored && stored in ACCENTS) return stored as Accent
  return "slate"
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(readTheme)
  const [resultsPosition, setResultsPosition] = useState<ResultsPosition>(readResultsPosition)
  const [accent, setAccent] = useState<Accent>(readAccent)
  const [systemPrefersDark, setSystemPrefersDark] = useState<boolean>(
    () => window.matchMedia("(prefers-color-scheme: dark)").matches,
  )

  useEffect(() => {
    const mql = window.matchMedia("(prefers-color-scheme: dark)")
    const onChange = () => setSystemPrefersDark(mql.matches)
    mql.addEventListener("change", onChange)
    return () => mql.removeEventListener("change", onChange)
  }, [])

  const resolvedTheme: ResolvedTheme =
    theme === "dark" ? "dark"
    : theme === "light" ? "light"
    : systemPrefersDark ? "dark" : "light"

  useEffect(() => {
    document.documentElement.classList.toggle("dark", resolvedTheme === "dark")
  }, [resolvedTheme])

  useEffect(() => {
    localStorage.setItem(THEME_KEY, theme)
  }, [theme])

  useEffect(() => {
    localStorage.setItem(RESULTS_POSITION_KEY, resultsPosition)
  }, [resultsPosition])

  useEffect(() => {
    localStorage.setItem(ACCENT_KEY, accent)
    document.documentElement.style.setProperty("--klee-accent", ACCENTS[accent])
  }, [accent])

  return (
    <SettingsContext.Provider
      value={{ theme, resolvedTheme, resultsPosition, accent, accents: ACCENTS, setTheme, setResultsPosition, setAccent }}
    >
      {children}
    </SettingsContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSettings() {
  const ctx = useContext(SettingsContext)
  if (ctx === null) throw new Error("useSettings must be used within SettingsProvider")
  return ctx
}
