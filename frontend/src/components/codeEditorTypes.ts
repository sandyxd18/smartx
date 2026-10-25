// Kept apart from CodeEditor.tsx so tests can stub the editor without loading Monaco.
export interface EditorDiagnostic {
  line: number;
  severity: "error" | "warning";
  message: string;
}

export interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  /**
   * Ctrl+Enter / Cmd+Enter inside the editor, with the text the editor holds right now.
   * Do not rely on `value` here: right after a keystroke React may not have re-rendered.
   */
  onRun: (currentCode: string) => void;
  /** Shown as squiggles and in the gutter; cleared when the list is empty. */
  diagnostics: EditorDiagnostic[];
  language: "verilog" | "systemverilog";
}
