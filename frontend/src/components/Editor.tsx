import { Editor as MonacoEditor } from "@monaco-editor/react"
import { useSettings } from "../context/SettingsContext"
import { defineKleeDarkTheme } from "../lib/editorThemes"
import { registerCCompletions } from "../lib/kleeCompletions"

type EditorProps = {
  value: string
  onChange: (next: string) => void
}

export function Editor({ value, onChange }: EditorProps) {
  const { resolvedTheme, fontSize } = useSettings()
  const monacoTheme = resolvedTheme === "dark" ? "klee-dark" : "vs-light"

  return (
    <MonacoEditor
      height="100%"
      language="c"
      theme={monacoTheme}
      value={value}
      onChange={(next) => onChange(next ?? "")}
      beforeMount={(monaco) => {
        defineKleeDarkTheme(monaco)
        registerCCompletions(monaco)
      }}
      options={{
        minimap: { enabled: false },
        fontSize,
        automaticLayout: true,
      }}
    />
  )
}
