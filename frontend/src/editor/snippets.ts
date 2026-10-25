import type { Snippet } from "../api/client";

/** Where new import lines go: after the last top-level import, else after a module
 * docstring, else at the top. Returns a 0-based line index. */
function importLine(lines: string[]): number {
  let last = -1;
  lines.forEach((line, i) => {
    if (/^(import|from) \S/.test(line)) last = i;
  });
  if (last >= 0) return last + 1;
  const first = lines[0]?.trimStart() ?? "";
  const quote = first.startsWith('"""')
    ? '"""'
    : first.startsWith("'''")
      ? "'''"
      : null;
  if (quote) {
    // A one-line docstring closes on its own line; otherwise find the closing quotes.
    if (first.length > 3 && first.slice(3).includes(quote)) return 1;
    const end = lines.findIndex((line, i) => i > 0 && line.includes(quote));
    if (end >= 0) return end + 1;
  }
  return 0;
}

/**
 * Insert a snippet into a Python file: imports it needs and that are missing go with
 * the other imports, the body goes at the end (snippets are top-level code).
 * Returns the new text and the 1-based line where the body starts.
 */
export function applySnippet(
  content: string,
  snippet: Snippet,
): { content: string; line: number } {
  const lines = content === "" ? [] : content.replace(/\n$/, "").split("\n");
  const present = new Set(lines.map((line) => line.trim()));
  const missing = snippet.imports.filter((line) => !present.has(line.trim()));
  if (missing.length > 0) {
    const at = importLine(lines);
    // A new import block before other code needs a blank line after it.
    const spacer =
      at < lines.length && lines[at]?.trim() !== "" && at === 0 ? [""] : [];
    lines.splice(at, 0, ...missing, ...spacer);
  }
  while (lines.length > 0 && lines[lines.length - 1]?.trim() === "")
    lines.pop();
  const head = lines.length > 0 ? [...lines, "", ""] : [];
  const body = snippet.body.replace(/\n*$/, "");
  return { content: [...head, body].join("\n") + "\n", line: head.length + 1 };
}
