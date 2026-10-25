import { useEffect, useId, useState, type ReactNode } from "react";
import {
  api,
  type ProjectDiagnostic,
  type ProjectRunSummary,
  type RunComparison,
  type SimResult,
} from "../api/client";
import { apiErrorMessage, httpErrorMessage, UNREACHABLE } from "../api/errors";
import { projectProblems, type ProjectRunState } from "../hooks/useProjectRun";
import { FpgaReport, FpgaSummary } from "./FpgaReport";
import { WaveView } from "./WaveView";

export type RunTab = "problems" | "tests" | "log" | "wave" | "fpga" | "history";

export interface RunPanelProps {
  projectId: number;
  lint: ProjectRunState;
  sim: ProjectRunState;
  fpga: ProjectRunState;
  tab: RunTab;
  onTab: (tab: RunTab) => void;
  /** Open the file of a problem at its line. */
  onOpen: (diagnostic: ProjectDiagnostic) => void;
  /** Show a past run from the history. */
  onOpenRun: (runId: string) => void;
}

const TABS: { id: RunTab; label: string }[] = [
  { id: "problems", label: "Problems" },
  { id: "tests", label: "Tests" },
  { id: "log", label: "Log" },
  { id: "wave", label: "Waveform" },
  { id: "fpga", label: "FPGA" },
  { id: "history", label: "Riwayat" },
];

function groupByFile(
  diagnostics: ProjectDiagnostic[],
): [string, ProjectDiagnostic[]][] {
  const groups = new Map<string, ProjectDiagnostic[]>();
  for (const d of diagnostics)
    groups.set(d.file, [...(groups.get(d.file) ?? []), d]);
  return [...groups.entries()];
}

function problemsSummary(
  lint: ProjectRunState,
  sim: ProjectRunState,
): ReactNode {
  const compileError = !sim.running && sim.run?.sim?.status === "compile_error";
  if (!compileError) return lintSummary(lint);
  return (
    <>
      <span className="font-medium text-red-700">
        Kode tidak bisa dikompilasi
      </span>
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
    return (
      <span className="text-red-700">
        {`Lint tidak selesai. ${run.error ?? ""}`.trim()}
      </span>
    );
  }
  const result = run.lint;
  if (!result || result.diagnostics.length === 0) return "Tidak ada masalah.";
  return `${result.errors} error, ${result.warnings} warning`;
}

function simVerdict(result: SimResult): { text: string; ok: boolean } {
  const failed = result.tests.filter((t) => !t.passed).length;
  switch (result.status) {
    case "pass":
      return {
        text: `Lulus semua test (${result.tests.length}/${result.tests.length})`,
        ok: true,
      };
    case "fail":
      return {
        text: `${failed} dari ${result.tests.length} test gagal`,
        ok: false,
      };
    case "compile_error":
      return { text: "Kode tidak bisa dikompilasi", ok: false };
    default:
      return {
        text: "Simulasi tidak menghasilkan hasil test. Lihat tab Log.",
        ok: false,
      };
  }
}

function simSummary(sim: ProjectRunState): ReactNode {
  if (sim.running)
    return sim.status === "queued" ? "Menunggu giliran…" : "Simulasi berjalan…";
  if (sim.error) return <span className="text-red-700">{sim.error}</span>;
  const run = sim.run;
  if (!run) return "Klik Simulasi untuk menjalankan testbench cocotb.";
  if (run.status !== "succeeded" || !run.sim) {
    return (
      <span className="text-red-700">{run.error ?? "Simulasi gagal."}</span>
    );
  }
  const verdict = simVerdict(run.sim);
  return (
    <>
      <span
        className={`font-medium ${verdict.ok ? "text-green-700" : "text-red-700"}`}
      >
        {verdict.text}
      </span>
      <span className="text-slate-500">
        {" "}
        · {run.sim.simulator_version || run.sim.simulator}
      </span>
    </>
  );
}

export function RunPanel({
  projectId,
  lint,
  sim,
  fpga,
  tab,
  onTab,
  onOpen,
  onOpenRun,
}: RunPanelProps) {
  const ids = {
    problems: useId(),
    tests: useId(),
    log: useId(),
    wave: useId(),
    fpga: useId(),
    history: useId(),
  };
  // Once opened, the waveform viewer stays mounted so switching tabs does not reload Surfer.
  const [waveOpened, setWaveOpened] = useState(tab === "wave");
  if (tab === "wave" && !waveOpened) setWaveOpened(true);
  // While a new simulation runs, keep the previous waveform instead of an empty panel.
  const [lastWave, setLastWave] = useState<string | null>(null);
  const currentWave = sim.run?.sim?.wave_url ?? null;
  if (currentWave !== null && currentWave !== lastWave)
    setLastWave(currentWave);
  const waveUrl = sim.running ? lastWave : currentWave;

  const problems = projectProblems(lint, sim, fpga);

  return (
    <section
      aria-label="Hasil run"
      className={`flex shrink-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white ${
        tab === "wave" ? "h-[32rem]" : tab === "fpga" ? "h-80" : "h-60"
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
                tab === t.id
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {t.label}
              {t.id === "problems" &&
                problems.length > 0 &&
                ` (${problems.length})`}
            </button>
          ))}
        </div>
        <div className="min-w-0 truncate text-slate-600">
          {tab === "problems" ? (
            problemsSummary(lint, sim)
          ) : tab === "history" ? (
            "Klik sebuah run untuk membuka hasilnya."
          ) : tab === "fpga" ? (
            <FpgaSummary fpga={fpga} />
          ) : (
            simSummary(sim)
          )}
        </div>
      </div>
      <div
        role="tabpanel"
        id={ids[tab]}
        aria-labelledby={`${ids[tab]}-tab`}
        className="min-h-0 flex-1 overflow-auto px-3 py-2 text-sm"
      >
        {tab === "problems" && (
          <ProblemList problems={problems} onOpen={onOpen} />
        )}
        {tab === "history" && (
          <HistoryList
            projectId={projectId}
            shown={[lint.run?.id, sim.run?.id, fpga.run?.id]}
            onOpenRun={onOpenRun}
          />
        )}
        {tab === "fpga" && (
          <FpgaReport
            fpga={fpga}
            onOpenSource={(file, line) =>
              onOpen({ file, line, severity: "warning", message: "" })
            }
          />
        )}
        {tab === "tests" && (
          <TestList result={sim.running ? null : (sim.run?.sim ?? null)} />
        )}
        {tab === "log" && (
          <pre className="font-mono text-xs whitespace-pre-wrap text-slate-700">
            {sim.running
              ? sim.lines.join("\n")
              : sim.run?.sim?.log || sim.run?.error || "Belum ada log."}
          </pre>
        )}
        {waveOpened && (
          <div className={tab === "wave" ? "h-full" : "hidden"}>
            {waveUrl ? (
              <WaveView url={waveUrl} />
            ) : (
              <p className="text-slate-500">
                Belum ada waveform. Jalankan Simulasi dulu.
              </p>
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
          <div className="font-mono text-xs font-medium text-slate-700">
            {file}
          </div>
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
  for (const t of result.tests)
    modules.set(t.module, [...(modules.get(t.module) ?? []), t]);
  return (
    <>
      {[...modules.entries()].map(([module, tests]) => (
        <div key={module} className="mb-2">
          <div className="font-mono text-xs font-medium text-slate-700">
            {module}
          </div>
          <ul className="space-y-1">
            {tests.map((t) => (
              <li key={t.name} className="flex gap-2">
                <span
                  className={t.passed ? "text-green-600" : "text-red-600"}
                  aria-hidden
                >
                  {t.passed ? "✓" : "✗"}
                </span>
                <div>
                  <div className="font-mono text-xs">{t.name}</div>
                  {t.message && (
                    <div className="text-xs text-red-700">{t.message}</div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </>
  );
}

const WHEN = new Intl.DateTimeFormat("id-ID", {
  dateStyle: "short",
  timeStyle: "medium",
});
const SECONDS = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 1 });
const KIND_LABELS: Record<string, string> = {
  lint: "Lint",
  sim: "Simulasi",
  fpga: "FPGA",
};
const SIMULATOR_LABELS: Record<string, string> = {
  icarus: "Icarus",
  verilator: "Verilator",
};
const STATUS_LABELS: Record<string, string> = {
  queued: "menunggu",
  running: "berjalan",
  succeeded: "selesai",
  failed: "gagal",
  cancelled: "dibatalkan",
  timeout: "timeout",
};

type HistoryState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ok"; runs: ProjectRunSummary[] };

function HistoryList(props: {
  projectId: number;
  /** Runs currently shown in the panel (marked in the list). */
  shown: (string | undefined)[];
  onOpenRun: (runId: string) => void;
}) {
  const { projectId } = props;
  const [state, setState] = useState<HistoryState>({ kind: "loading" });
  // Up to two simulations picked for comparison, in the order they were picked.
  const [picked, setPicked] = useState<string[]>([]);
  const [comparison, setComparison] = useState<RunComparison | null>(null);
  const [compareError, setCompareError] = useState<string | null>(null);

  function togglePick(runId: string) {
    setPicked((current) =>
      current.includes(runId)
        ? current.filter((id) => id !== runId)
        : [...current, runId].slice(-2),
    );
  }

  async function compare() {
    const [a, b] = picked;
    if (!a || !b) return;
    setCompareError(null);
    try {
      const { data, error, response } = await api.GET(
        "/api/projects/{project_id}/runs/compare",
        {
          params: { path: { project_id: projectId }, query: { a, b } },
        },
      );
      if (data) setComparison(data);
      else setCompareError(apiErrorMessage(error, response.status));
    } catch {
      setCompareError(UNREACHABLE);
    }
  }

  // Read on every opening of the tab, so runs that just finished are there.
  useEffect(() => {
    let cancelled = false;
    api
      .GET("/api/projects/{project_id}/runs", {
        params: { path: { project_id: projectId } },
      })
      .then(
        ({ data, response }) => {
          if (cancelled) return;
          setState(
            data
              ? { kind: "ok", runs: data }
              : { kind: "error", message: httpErrorMessage(response.status) },
          );
        },
        () => {
          if (!cancelled) setState({ kind: "error", message: UNREACHABLE });
        },
      );
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  if (state.kind === "loading")
    return <p className="text-slate-500">Memuat riwayat…</p>;
  if (state.kind === "error")
    return <p className="text-red-700">{state.message}</p>;
  if (state.runs.length === 0) {
    return (
      <p className="text-slate-500">
        Belum ada run. Klik Lint, Simulasi, atau Build.
      </p>
    );
  }
  if (comparison) {
    return (
      <ComparisonView
        comparison={comparison}
        onBack={() => setComparison(null)}
      />
    );
  }
  return (
    <>
      <div className="mb-1 flex items-center gap-2 text-xs">
        <button
          type="button"
          onClick={() => void compare()}
          disabled={picked.length !== 2}
          className="rounded border border-slate-300 px-2 py-0.5 disabled:opacity-50"
        >
          Bandingkan
        </button>
        <span className="text-slate-500">
          Centang dua simulasi untuk melihat test yang berubah status.
        </span>
        {compareError && <span className="text-red-700">{compareError}</span>}
      </div>
      <ul aria-label="Riwayat run" className="divide-y divide-slate-100">
        {state.runs.map((run) => {
          const ok = run.status === "succeeded";
          const comparable = ok && run.kind === "sim";
          return (
            <li key={run.id} className="flex items-center gap-1">
              <span className="w-5 shrink-0 text-center">
                {comparable && (
                  <input
                    type="checkbox"
                    aria-label={`Pilih run ${WHEN.format(new Date(run.created_at))} untuk dibandingkan`}
                    checked={picked.includes(run.id)}
                    onChange={() => togglePick(run.id)}
                  />
                )}
              </span>
              <button
                type="button"
                aria-current={props.shown.includes(run.id) ? "true" : undefined}
                onClick={() => props.onOpenRun(run.id)}
                disabled={run.status === "queued" || run.status === "running"}
                className="flex w-full items-baseline gap-3 rounded px-2 py-1 text-left text-xs hover:bg-slate-100 aria-[current=true]:bg-slate-100"
              >
                <span className="w-36 shrink-0 text-slate-500">
                  {WHEN.format(new Date(run.created_at))}
                </span>
                <span className="w-28 shrink-0 font-medium">
                  {KIND_LABELS[run.kind] ?? run.kind}
                  {run.simulator
                    ? ` · ${SIMULATOR_LABELS[run.simulator] ?? run.simulator}`
                    : ""}
                </span>
                <span
                  className={`w-20 shrink-0 ${ok ? "text-slate-600" : "text-red-700"}`}
                >
                  {STATUS_LABELS[run.status] ?? run.status}
                </span>
                <span className="w-16 shrink-0 text-slate-500">
                  {run.duration_s === null || run.duration_s === undefined
                    ? ""
                    : `${SECONDS.format(run.duration_s)} dtk`}
                </span>
                <span className="min-w-0 truncate">{run.summary ?? ""}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </>
  );
}

const CHANGE_LABELS: Record<string, string> = {
  broken: "Rusak",
  fixed: "Diperbaiki",
  added: "Baru",
  removed: "Hilang",
  same: "Sama",
};
const CHANGE_TONES: Record<string, string> = {
  broken: "text-red-700",
  fixed: "text-green-700",
  added: "text-slate-700",
  removed: "text-amber-800",
  same: "text-slate-500",
};
const STATE_LABELS: Record<string, string> = {
  passed: "lulus",
  failed: "gagal",
  missing: "tidak ada",
};

function ComparisonView(props: {
  comparison: RunComparison;
  onBack: () => void;
}) {
  const { comparison } = props;
  const changed = comparison.tests.filter((t) => t.change !== "same");
  const same = comparison.tests.length - changed.length;
  const side = (label: string, run: RunComparison["before"]) => (
    <div>
      <span className="font-medium">{label}:</span>{" "}
      {WHEN.format(new Date(run.created_at))}
      {run.simulator
        ? ` · ${SIMULATOR_LABELS[run.simulator] ?? run.simulator}`
        : ""}{" "}
      · {run.summary ?? ""}
    </div>
  );
  return (
    <section
      aria-label="Perbandingan run"
      className="flex flex-col gap-2 text-xs"
    >
      <div>
        <button
          type="button"
          onClick={props.onBack}
          className="text-slate-600 hover:underline"
        >
          ← Kembali ke riwayat
        </button>
      </div>
      {side("Sebelum", comparison.before)}
      {side("Sesudah", comparison.after)}
      <div className="flex flex-wrap gap-3">
        {(["broken", "fixed", "added", "removed"] as const).map((kind) => (
          <span key={kind} className={CHANGE_TONES[kind]}>
            {CHANGE_LABELS[kind]}: {comparison.counts[kind] ?? 0}
          </span>
        ))}
      </div>
      {changed.length === 0 ? (
        <p className="text-slate-500">Tidak ada test yang berubah status.</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {changed.map((t) => (
            <li key={`${t.module}.${t.name}`} className="flex gap-3 py-0.5">
              <span
                className={`w-20 shrink-0 font-medium ${CHANGE_TONES[t.change] ?? ""}`}
              >
                {CHANGE_LABELS[t.change] ?? t.change}
              </span>
              <span className="min-w-0 flex-1 truncate font-mono">
                {t.module}.{t.name}
              </span>
              <span className="shrink-0 text-slate-600">
                {STATE_LABELS[t.before]} → {STATE_LABELS[t.after]}
              </span>
            </li>
          ))}
        </ul>
      )}
      {same > 0 && <p className="text-slate-500">{same} test tidak berubah</p>}
    </section>
  );
}
