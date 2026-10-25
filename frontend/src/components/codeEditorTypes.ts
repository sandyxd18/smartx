// Kept apart from CodeEditor.tsx so tests can stub the editor without loading Monaco.
export interface EditorDiagnostic {
  line: number;
  severity: "error" | "warning";
  message: string;
  /** 1-based; without it the whole line is marked. */
  column?: number | null;
  /** 1-based, exclusive; without it the word at `column` is marked. */
  endColumn?: number | null;
  /** Tool-specific name such as Verilator's LATCH. */
  code?: string | null;
}

export type EditorLanguage =
  | "verilog"
  | "systemverilog"
  | "python"
  | "yaml"
  | "markdown"
  | "plaintext";

export interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  /**
   * Ctrl+Enter / Cmd+Enter inside the editor, with the text the editor holds right now.
   * Do not rely on `value` here: right after a keystroke React may not have re-rendered.
   */
  onRun?: (currentCode: string) => void;
  /** Shown as squiggles and in the gutter; cleared when the list is empty. */
  diagnostics?: EditorDiagnostic[];
  language: EditorLanguage;
  /** Move the cursor here and scroll to it; a new object jumps again. */
  reveal?: { line: number; column?: number } | null;
}
