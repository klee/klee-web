import type { BeforeMount } from "@monaco-editor/react";

const kleeDarkTheme = {
  base: "vs-dark" as const,
  inherit: true,
  rules: [] as const,
  colors: {
    "editor.background": "#020617",
    "editor.foreground": "#f1f5f9",
    "editorGutter.background": "#0f172a",
    "editorGutter.decoratorBackground": "#1e293b",
    "editorLineNumber.foreground": "#64748b",
    "editorLineNumber.activeForeground": "#cbd5e1",
    "editorLineNumber.background": "#0f172a",
    "editor.selectionBackground": "#334155",
    "editor.inactiveSelectionBackground": "#1e293b",
    "editor.selectionHighlightBackground": "#334155",
    "editor.lineHighlightBackground": "#0f172a",
    "editorCursor.foreground": "#f1f5f9",
    "editorWidget.background": "#0f172a",
    "editorWidget.border": "#334155",
    "input.background": "#020617",
    "input.border": "#334155",
    "input.foreground": "#f1f5f9",
    "input.placeholderForeground": "#64748b",
    focusBorder: "#475569",
    "minimap.background": "#020617",
    "diffEditor.border": "#334155",
  },
};

export const defineKleeDarkTheme: BeforeMount = (monaco) => {
  monaco.editor.defineTheme("klee-dark", kleeDarkTheme);
};
