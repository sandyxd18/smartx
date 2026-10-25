import type { EditorLanguage } from "../components/codeEditorTypes";

const BY_EXTENSION: Record<string, EditorLanguage> = {
  v: "verilog",
  vh: "verilog",
  sv: "systemverilog",
  svh: "systemverilog",
  py: "python",
  yaml: "yaml",
  yml: "yaml",
  md: "markdown",
};

/** Monaco language for a project file, from its extension. */
export function languageForPath(path: string): EditorLanguage {
  const name = path.slice(path.lastIndexOf("/") + 1);
  const dot = name.lastIndexOf(".");
  if (dot <= 0) return "plaintext";
  return BY_EXTENSION[name.slice(dot + 1).toLowerCase()] ?? "plaintext";
}
