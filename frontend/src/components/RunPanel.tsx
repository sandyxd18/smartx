import { useId, useState, type ReactNode } from "react";
import type { ProjectDiagnostic, SimResult } from "../api/client";
import { projectProblems, type ProjectRunState } from "../hooks/useProjectRun";
import { WaveView } from "./WaveView";

export type RunTab = "problems" | "tests" | "log" | "wave";

export interface RunPanelProps {
  lint: ProjectRunState;
  sim: ProjectRunState;
  tab: RunTab;
  onTab: (tab: RunTab) => void;
  /** Open the file of a problem at its line. */
  onOpen: (diagnostic: ProjectDiagnostic) => void;
}

const TABS: { id: RunTab; label: string }[] = [
  { id: "problems", label: "Problems" },
  { id: "tests", label: "Tests" },
  { id: "log", label: "Log" },
  { id: "wave", label: "Waveform" },
];

function groupByFile(diagnostics: ProjectDiagnostic[]): [string, ProjectDiagnostic[]][] {
  const groups = new Map<string, ProjectDiagnostic[]>();
  for (const d of diagnostics) groups.set(d.file, [...(groups.get(d.file) ?? []), d]);
  return [...groups.entries()];
}

function problemsSummary(lint: ProjectRunState, sim: ProjectRunState): ReactNode {
  const compileError = !sim.running && sim.run?.sim?.status === "compile_error";
  if (!compileError) return lintSummary(lint);
  return (
    <>
      <span className="font-medium text-red-700">Kode tidak bisa dikompilasi</span>
      {lint.run || lint.running ? <> · {lintSummary(lint)}</> : null}
    </>
  );
}

function lintSummary(lint: ProjectRunState): ReactNode {
  if (lint.running) return "Lint berjalan…";
  if (lint.error) return <span className="text-red-700">{lint.error}</span>;
  const run = lint.run;
  if (!run) return "Klik Lint untuk memeriksa kode dengan Verilator.";
  if (run.status !== "succeeded") {
    return <span className="text-red-700">{`Lint tidak selesai. ${run.error ?? ""}`.trim()}</span>;
  }
  const result = run.lint;
  if (!result || result.diagnostics.length === 0) return "Tidak ada masalah.";
  return `${result.errors} error, ${result.warnings} warning`;
}

function simVerdict(result: SimResult): { text: string; ok: boolean } {
  const failed = result.tests.filter((t) => !t.passed).length;
  switch (result.status) {
    case "pass":
      return { text: `Lulus semua test (${result.tests.length}/${result.tests.length})`, ok: true };
    case "fail":
      return { text: `${failed} dari ${result.tests.length} test gagal`, ok: false };
    case "compile_error":
      return { text: "Kode tidak bisa dikompilasi", ok: false };
    default:
      return { text: "Simulasi tidak menghasilkan hasil test. Lihat tab Log.", ok: false };
  }
}

function simSummary(sim: ProjectRunState): ReactNode {
  if (sim.running) return sim.status === "queued" ? "Menunggu giliran…" : "Simulasi berjalan…";
  if (sim.error) return <span className="text-red-700">{sim.error}</span>;
  const run = sim.run;
  if (!run) return "Klik Simulasi untuk menjalankan testbench cocotb.";
  if (run.status !== "succeeded" || !run.sim) {
    return <span className="text-red-700">{run.error ?? "Simulasi gagal."}</span>;
  }
  const verdict = simVerdict(run.sim);
  return (
    <>
      <span className={`font-medium ${verdict.ok ? "text-green-700" : "text-red-700"}`}>
        {verdict.text}
      </span>
      <span className="text-slate-500"> · {run.sim.simulator_version || run.sim.simulator}</span>
    </>
  );
}

export function RunPanel({ lint, sim, tab, onTab, onOpen }: RunPanelProps) {
  const ids = { problems: useId(), tests: useId(), log: useId(), wave: useId() };
  // Once opened, the waveform viewer stays mounted so switching tabs does not reload Surfer.
  const [waveOpened, setWaveOpened] = useState(tab === "wave");
  if (tab === "wave" && !waveOpened) setWaveOpened(true);
  // While a new simulation runs, keep the previous waveform instead of an empty panel.
  const [lastWave, setLastWave] = useState<string | null>(null);
  const currentWave = sim.run?.sim?.wave_url ?? null;
  if (currentWave !== null && currentWave !== lastWave) setLastWave(currentWave);
  const waveUrl = sim.running ? lastWave : currentWave;

  const problems = projectProblems(lint, sim);

  return (
    <section
      aria-label="Hasil run"
      className={`flex shrink-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white ${
        tab === "wave" ? "h-[32rem]" : "h-60"
      }`}
    >
      <div className="flex items-center gap-3 border-b border-slate-200 px-3 py-1.5 text-xs">
        <div role="tablist" className="flex shrink-0 gap-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              id={`${ids[t.id]}-tab`}
              aria-controls={ids[t.id]}
              aria-selected={tab === t.id}
              onClick={() => onTab(t.id)}
              className={`rounded px-2 py-0.5 ${
                tab === t.id ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {t.label}
              {t.id === "problems" && problems.length > 0 && ` (${problems.length})`}
            </button>
          ))}
        </div>
        <div className="min-w-0 truncate text-slate-600">
          {tab === "problems" ? problemsSummary(lint, sim) : simSummary(sim)}
        </div>
      </div>
      <div
        role="tabpanel"
        id={ids[tab]}
        aria-labelledby={`${ids[tab]}-tab`}
        className="min-h-0 flex-1 overflow-auto px-3 py-2 text-sm"
      >
        {tab === "problems" && <ProblemList problems={problems} onOpen={onOpen} />}
        {tab === "tests" && <TestList result={sim.running ? null : (sim.run?.sim ?? null)} />}
        {tab === "log" && (
          <pre className="font-mono text-xs whitespace-pre-wrap text-slate-700">
            {sim.running ? sim.lines.join("\n") : sim.run?.sim?.log || sim.run?.error || "Belum ada log."}
          </pre>
        )}
        {waveOpened && (
          <div className={tab === "wave" ? "h-full" : "hidden"}>
            {waveUrl ? (
              <WaveView url={waveUrl} />
            ) : (
              <p className="text-slate-500">Belum ada waveform. Jalankan Simulasi dulu.</p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

function ProblemList(props: {
  problems: ProjectDiagnostic[];
  onOpen: (diagnostic: ProjectDiagnostic) => void;
}) {
  if (props.problems.length === 0) return null;
  return (
    <>
      {groupByFile(props.problems).map(([file, items]) => (
        <div key={file} className="mb-2">
          <div className="font-mono text-xs font-medium text-slate-700">{file}</div>
          <ul aria-label={`Masalah di ${file}`}>
            {items.map((d, i) => (
              <li key={i}>
                <button
                  type="button"
                  onClick={() => props.onOpen(d)}
                  className={`w-full rounded px-2 py-0.5 text-left font-mono text-xs hover:bg-slate-100 ${
                    d.severity === "error" ? "text-red-700" : "text-amber-800"
                  }`}
                >
                  {d.line}
                  {d.col ? `:${d.col}` : ""} {d.message}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </>
  );
}

function TestList({ result }: { result: SimResult | null }) {
  if (!result || result.tests.length === 0) return null;
  const modules = new Map<string, SimResult["tests"]>();
  for (const t of result.tests) modules.set(t.module, [...(modules.get(t.module) ?? []), t]);
  return (
    <>
      {[...modules.entries()].map(([module, tests]) => (
        <div key={module} className="mb-2">
          <div className="font-mono text-xs font-medium text-slate-700">{module}</div>
          <ul className="space-y-1">
            {tests.map((t) => (
              <li key={t.name} className="flex gap-2">
                <span className={t.passed ? "text-green-600" : "text-red-600"} aria-hidden>
                  {t.passed ? "✓" : "✗"}
                </span>
                <div>
                  <div className="font-mono text-xs">{t.name}</div>
                  {t.message && <div className="text-xs text-red-700">{t.message}</div>}
                </div>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </>
  );
}
