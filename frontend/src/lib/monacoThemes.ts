const S = {
  50: "#f8fafc",
  100: "#f1f5f9",
  200: "#e2e8f0",
  300: "#cbd5e1",
  400: "#94a3b8",
  500: "#64748b",
  600: "#475569",
  700: "#334155",
  800: "#1e293b",
  900: "#0f172a",
  950: "#020617",
} as const

const LIGHT_COLORS: Record<string, string> = {
  "editor.background": "#ffffff",
  "editor.foreground": S[900],
  "editorLineNumber.foreground": S[400],
  "editorLineNumber.activeForeground": S[600],
  "editor.selectionBackground": `${S[300]}80`,
  "editor.inactiveSelectionBackground": `${S[200]}80`,
  "editorCursor.foreground": S[700],
  "editorGutter.background": S[50],
  "editor.lineHighlightBackground": S[100],
  "editorLineNumber.dimmedForeground": S[300],
  "editorBracketMatch.background": `${S[200]}60`,
  "editorBracketMatch.border": S[300],
}

const DARK_COLORS: Record<string, string> = {
  "editor.background": S[950],
  "editor.foreground": S[100],
  "editorLineNumber.foreground": S[600],
  "editorLineNumber.activeForeground": S[400],
  "editor.selectionBackground": `${S[700]}80`,
  "editor.inactiveSelectionBackground": `${S[800]}80`,
  "editorCursor.foreground": S[100],
  "editorGutter.background": S[950],
  "editor.lineHighlightBackground": S[900],
  "editorLineNumber.dimmedForeground": S[700],
  "editorBracketMatch.background": `${S[700]}50`,
  "editorBracketMatch.border": S[600],
}

export const KLEE_THEME_LIGHT = "klee-light"
export const KLEE_THEME_DARK = "klee-dark"

interface MonacoLike {
  editor: {
    defineTheme(
      themeName: string,
      themeData: {
        base: "vs" | "vs-dark" | "hc-black" | "hc-light"
        inherit: boolean
        rules: Array<{
          token: string
          foreground?: string
          background?: string
          fontStyle?: string
        }>
        colors: Record<string, string>
      },
    ): void
  }
}

export function defineKleeThemes(monaco: MonacoLike) {
  monaco.editor.defineTheme(KLEE_THEME_LIGHT, {
    base: "vs",
    inherit: true,
    rules: [],
    colors: LIGHT_COLORS,
  })
  monaco.editor.defineTheme(KLEE_THEME_DARK, {
    base: "vs-dark",
    inherit: true,
    rules: [],
    colors: DARK_COLORS,
  })
}
