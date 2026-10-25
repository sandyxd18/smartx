import type { LintDiagnostic, ProjectRun } from "../api/client";

export interface ProblemsPanelProps {
  run: ProjectRun | null;
  running: boolean;
  /** A run that could not start, or whose result could not be read. */
  error: string | null;
  onOpen: (diagnostic: LintDiagnostic) => void;
}

function groupByFile(diagnostics: LintDiagnostic[]): [string, LintDiagnostic[]][] {
  const groups = new Map<string, LintDiagnostic[]>();
  for (const d of diagnostics) groups.set(d.file, [...(groups.get(d.file) ?? []), d]);
  return [...groups.entries()];
}

export function ProblemsPanel({ run, running, error, onOpen }: ProblemsPanelProps) {
  const lint = run?.lint ?? null;
  let summary: string;
  if (running) summary = "Lint berjalan…";
  else if (error) summary = "";
  else if (!run) summary = "Klik Lint untuk memeriksa kode dengan Verilator.";
  else if (run.status !== "succeeded") summary = `Lint tidak selesai. ${run.error ?? ""}`.trim();
  else if (!lint || lint.diagnostics.length === 0) summary = "Tidak ada masalah.";
  else summary = `${lint.errors} error, ${lint.warnings} warning`;

  return (
    <section
      aria-label="Problems"
      className="flex max-h-56 min-h-0 flex-col rounded-lg border border-slate-200 bg-white"
    >
      <div className="flex items-center gap-3 border-b border-slate-200 px-3 py-1.5 text-xs">
        <span className="font-medium">Problems</span>
        {summary && <span className="text-slate-600">{summary}</span>}
        {error && <span className="text-red-700">{error}</span>}
      </div>
      {!running && lint && lint.diagnostics.length > 0 && (
        <div className="min-h-0 overflow-auto px-3 py-2">
          {groupByFile(lint.diagnostics).map(([file, items]) => (
            <div key={file} className="mb-2">
              <div className="font-mono text-xs font-medium text-slate-700">{file}</div>
              <ul aria-label={`Masalah di ${file}`}>
                {items.map((d, i) => (
                  <li key={i}>
                    <button
                      type="button"
                      onClick={() => onOpen(d)}
                      className={`w-full rounded px-2 py-0.5 text-left font-mono text-xs hover:bg-slate-100 ${
                        d.severity === "error" ? "text-red-700" : "text-amber-800"
                      }`}
                    >
                      {d.line}:{d.col} {d.message}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
