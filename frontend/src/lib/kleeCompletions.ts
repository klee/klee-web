import type { Monaco } from "@monaco-editor/react";

export type CompletionSpec = {
  label: string;
  kind: "snippet" | "function" | "module";
  insertText: string;
  snippet?: boolean;
  detail?: string;
  documentation?: string;
};

// Curated, static completions for the C editor: KLEE intrinsics as snippets plus
// a small set of common C calls and includes. Deliberately monaco-free data so it
// unit-tests in the node environment; createCCompletionProvider maps it to the
// monaco API at registration time.
export const COMPLETIONS: CompletionSpec[] = [
  {
    label: "klee_make_symbolic",
    kind: "snippet",
    snippet: true,
    insertText: 'klee_make_symbolic(&${1:var}, sizeof(${1:var}), "${2:name}")',
    detail: "Mark memory symbolic",
    documentation: "Make the bytes at an address symbolic under the given name.",
  },
  {
    label: "klee_assume",
    kind: "snippet",
    snippet: true,
    insertText: "klee_assume(${1:condition})",
    detail: "Constrain the path",
    documentation: "Assume a condition holds; paths that violate it are dropped.",
  },
  {
    label: "klee_assert",
    kind: "snippet",
    snippet: true,
    insertText: "klee_assert(${1:condition})",
    detail: "Assert a condition",
    documentation: "Report an error on any path where the condition is false.",
  },
  {
    label: "klee_range",
    kind: "snippet",
    snippet: true,
    insertText: 'klee_range(${1:begin}, ${2:end}, "${3:name}")',
    detail: "Symbolic int in a range",
    documentation: "Return a fresh symbolic int constrained to [begin, end).",
  },
  {
    label: "klee_int",
    kind: "snippet",
    snippet: true,
    insertText: 'klee_int("${1:name}")',
    detail: "Fresh symbolic int",
    documentation: "Return a fresh unconstrained symbolic int with the given name.",
  },
  {
    label: "klee_get_valuef",
    kind: "snippet",
    snippet: true,
    insertText: "klee_get_valuef(${1:expr})",
    detail: "Concretize a float",
    documentation: "Return a concrete float consistent with the current path.",
  },
  {
    label: "klee_get_valued",
    kind: "snippet",
    snippet: true,
    insertText: "klee_get_valued(${1:expr})",
    detail: "Concretize a double",
    documentation: "Return a concrete double consistent with the current path.",
  },
  {
    label: "klee_prefer_cex",
    kind: "snippet",
    snippet: true,
    insertText: "klee_prefer_cex(${1:object}, ${2:condition})",
    detail: "Prefer counterexamples",
    documentation: "Prefer test cases that satisfy the condition, when feasible.",
  },
  {
    label: "klee_silent_exit",
    kind: "snippet",
    snippet: true,
    insertText: "klee_silent_exit(${1:0})",
    detail: "Exit without a test case",
    documentation: "Terminate the current path without generating a test case.",
  },
  {
    label: "klee_abort",
    kind: "function",
    insertText: "klee_abort()",
    detail: "Abort the current path",
    documentation: "Terminate the current path with an abort error.",
  },
  {
    label: "klee_warning",
    kind: "snippet",
    snippet: true,
    insertText: 'klee_warning("${1:message}")',
    detail: "Emit a KLEE warning",
    documentation: "Emit a warning to the KLEE log for the current path.",
  },
  {
    label: "klee_print_expr",
    kind: "snippet",
    snippet: true,
    insertText: 'klee_print_expr("${1:msg}", ${2:expr})',
    detail: "Print an expression",
    documentation: "Print a message and the value of an expression to the KLEE log.",
  },
  {
    label: "#include <klee/klee.h>",
    kind: "module",
    insertText: "#include <klee/klee.h>",
    detail: "KLEE intrinsics header",
  },
  {
    label: "printf",
    kind: "function",
    snippet: true,
    insertText: "printf(${1})",
    detail: "stdio.h",
  },
  {
    label: "malloc",
    kind: "function",
    snippet: true,
    insertText: "malloc(${1})",
    detail: "stdlib.h",
  },
  {
    label: "free",
    kind: "function",
    snippet: true,
    insertText: "free(${1})",
    detail: "stdlib.h",
  },
  {
    label: "memcpy",
    kind: "function",
    snippet: true,
    insertText: "memcpy(${1})",
    detail: "string.h",
  },
  {
    label: "strlen",
    kind: "function",
    snippet: true,
    insertText: "strlen(${1})",
    detail: "string.h",
  },
  {
    label: "assert",
    kind: "function",
    snippet: true,
    insertText: "assert(${1})",
    detail: "assert.h",
  },
  { label: "#include <stdio.h>", kind: "module", insertText: "#include <stdio.h>" },
  { label: "#include <stdlib.h>", kind: "module", insertText: "#include <stdlib.h>" },
  { label: "#include <string.h>", kind: "module", insertText: "#include <string.h>" },
  { label: "#include <assert.h>", kind: "module", insertText: "#include <assert.h>" },
];

// monaco-editor is not a dependency (the wrapper loads Monaco at runtime), so
// rather than pull it in just for types we structurally type the two fields we
// read off the model and position. `monaco` is the wrapper's Monaco handle.
type EditorPosition = { lineNumber: number; column: number };
type EditorModel = {
  getWordUntilPosition(position: EditorPosition): { startColumn: number; endColumn: number };
};

export function createCCompletionProvider(monaco: Monaco) {
  const kindMap = {
    snippet: monaco.languages.CompletionItemKind.Snippet,
    function: monaco.languages.CompletionItemKind.Function,
    module: monaco.languages.CompletionItemKind.Module,
  };
  const snippetRule = monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet;

  return {
    provideCompletionItems(model: EditorModel, position: EditorPosition) {
      const word = model.getWordUntilPosition(position);
      const range = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn,
      };
      const suggestions = COMPLETIONS.map((c) => ({
        label: c.label,
        kind: kindMap[c.kind],
        insertText: c.insertText,
        insertTextRules: c.snippet ? snippetRule : undefined,
        detail: c.detail,
        documentation: c.documentation,
        range,
      }));
      return { suggestions };
    },
  };
}

let registered = false;

// Registered once for the app: a module-level guard so a remount or StrictMode's
// double-invoke cannot stack duplicate providers (which would double every suggestion).
export function registerCCompletions(monaco: Monaco): void {
  if (registered) return;
  registered = true;
  monaco.languages.registerCompletionItemProvider("c", createCCompletionProvider(monaco));
}
