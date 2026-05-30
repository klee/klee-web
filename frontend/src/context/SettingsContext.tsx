import { createContext, useContext, useEffect, useState, type ReactNode } from "react"

type Theme = "system" | "dark" | "light"
type ResolvedTheme = "dark" | "light"
type ResultsPosition = "right" | "below"
type AccentColor = string

type SettingsValue = {
  theme: Theme
  resolvedTheme: ResolvedTheme
  resultsPosition: ResultsPosition
  fontSize: number
  accentColor: AccentColor
  setTheme: (t: Theme) => void
  setResultsPosition: (p: ResultsPosition) => void
  setFontSize: (s: number) => void
  setAccentColor: (c: AccentColor) => void
}

const SettingsContext = createContext<SettingsValue | null>(null)

const THEME_KEY = "klee.theme"
const RESULTS_POSITION_KEY = "klee.resultsPosition"
const FONT_SIZE_KEY = "klee.fontSize"
const ACCENT_COLOR_KEY = "klee.accentColor"

const DEFAULT_ACCENT = "#475569"

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

function readFontSize(): number {
  const stored = localStorage.getItem(FONT_SIZE_KEY)
  if (stored !== null) {
    const n = Number(stored)
    if (Number.isFinite(n) && n >= 8 && n <= 32) return n
  }
  return 14
}

function readAccentColor(): string {
  const stored = localStorage.getItem(ACCENT_COLOR_KEY)
  return stored ?? DEFAULT_ACCENT
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(readTheme)
  const [resultsPosition, setResultsPosition] = useState<ResultsPosition>(readResultsPosition)
  const [fontSize, setFontSize] = useState<number>(readFontSize)
  const [accentColor, setAccentColor] = useState<string>(readAccentColor)
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

  // Set accent CSS variable on mount too (effect runs after render, so this ensures it's applied)
  useEffect(() => {
    document.documentElement.style.setProperty("--klee-accent", accentColor)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    localStorage.setItem(RESULTS_POSITION_KEY, resultsPosition)
  }, [resultsPosition])

  useEffect(() => {
    localStorage.setItem(FONT_SIZE_KEY, String(fontSize))
  }, [fontSize])

  useEffect(() => {
    localStorage.setItem(ACCENT_COLOR_KEY, accentColor)
    document.documentElement.style.setProperty("--klee-accent", accentColor)
  }, [accentColor])

  return (
    <SettingsContext.Provider
      value={{ theme, resolvedTheme, resultsPosition, fontSize, accentColor, setTheme, setResultsPosition, setFontSize, setAccentColor }}
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
