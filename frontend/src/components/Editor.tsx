import { Editor as MonacoEditor } from "@monaco-editor/react"
import { useSettings } from "../context/SettingsContext"
import {
  defineKleeThemes,
  KLEE_THEME_DARK,
  KLEE_THEME_LIGHT,
} from "../lib/monacoThemes"

type EditorProps = {
  value: string
  onChange: (next: string) => void
}

export function Editor({ value, onChange }: EditorProps) {
  const { resolvedTheme, fontSize } = useSettings()
  const monacoTheme = resolvedTheme === "dark" ? KLEE_THEME_DARK : KLEE_THEME_LIGHT

  return (
    <MonacoEditor
      height="100%"
      language="c"
      theme={monacoTheme}
      value={value}
      beforeMount={defineKleeThemes}
      onChange={(next) => onChange(next ?? "")}
      options={{
        minimap: { enabled: false },
        fontSize,
        automaticLayout: true,
      }}
    />
  )
}
