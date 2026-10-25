import type { CodeEditorProps } from "../components/codeEditorTypes";

/** Monaco does not run in jsdom; tests get a textarea with the same props. */
export function FakeCodeEditor({ value, onChange, onRun, diagnostics }: CodeEditorProps) {
  return (
    <div>
      <textarea
        aria-label="Editor kode"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if ((e.ctrlKey || e.metaKey) && e.key === "Enter") onRun(e.currentTarget.value);
        }}
      />
      <ul aria-label="Penanda editor">
        {diagnostics.map((d) => (
          <li key={`${d.line}-${d.message}`}>
            {d.severity} {d.line}: {d.message}
          </li>
        ))}
      </ul>
    </div>
  );
}
