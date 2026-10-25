import Editor, { type OnMount } from "@monaco-editor/react";
import { useEffect, useRef, useState } from "react";
import { monaco } from "../editor/monaco";
import type { CodeEditorProps } from "./codeEditorTypes";

type StandaloneEditor = Parameters<OnMount>[0];

const MARKER_OWNER = "smartx-grader";

export function CodeEditor({ value, onChange, onRun, diagnostics, language }: CodeEditorProps) {
  const [editor, setEditor] = useState<StandaloneEditor | null>(null);
  // The keybinding is registered once; read the latest callback through a ref.
  const onRunRef = useRef(onRun);
  useEffect(() => {
    onRunRef.current = onRun;
  }, [onRun]);

  const handleMount: OnMount = (instance) => {
    instance.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () =>
      onRunRef.current(instance.getValue()),
    );
    setEditor(instance);
  };

  useEffect(() => {
    const model = editor?.getModel();
    if (!model) return;
    const lastLine = model.getLineCount();
    monaco.editor.setModelMarkers(
      model,
      MARKER_OWNER,
      diagnostics.map((d) => {
        // Icarus sometimes reports the line after the last one (e.g. a missing endmodule).
        const line = Math.min(Math.max(d.line, 1), lastLine);
        const maxColumn = model.getLineMaxColumn(line);
        // Verilator points at a column: underline the word there, not the whole line.
        const column = d.column ? Math.min(d.column, maxColumn) : null;
        const word = column ? model.getWordAtPosition({ lineNumber: line, column }) : null;
        return {
          startLineNumber: line,
          endLineNumber: line,
          startColumn: word?.startColumn ?? column ?? 1,
          endColumn: word?.endColumn ?? (column ? Math.min(column + 1, maxColumn) : maxColumn),
          message: d.message,
          code: d.code ?? undefined,
          severity:
            d.severity === "warning" ? monaco.MarkerSeverity.Warning : monaco.MarkerSeverity.Error,
        };
      }),
    );
  }, [editor, diagnostics, value]);

  return (
    <Editor
      language={language}
      value={value}
      onChange={(v) => onChange(v ?? "")}
      onMount={handleMount}
      loading={<div className="p-3 text-sm text-slate-500">Memuat editor…</div>}
      options={{
        minimap: { enabled: false },
        fontSize: 14,
        tabSize: 2,
        insertSpaces: true,
        scrollBeyondLastLine: false,
        automaticLayout: true,
        renderWhitespace: "boundary",
      }}
    />
  );
}
