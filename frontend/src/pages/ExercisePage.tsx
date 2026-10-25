import { useCallback, useEffect, useId, useState } from "react";
import { Link, useParams } from "react-router";
import {
  api,
  TERMINAL_STATUSES,
  type ExerciseDetail,
  type ExerciseRun,
  type GradeResult,
} from "../api/client";
import { httpErrorMessage, UNREACHABLE } from "../api/errors";
import { CodeEditor } from "../components/CodeEditor";
import type { EditorDiagnostic } from "../components/codeEditorTypes";
import { Markdown } from "../components/Markdown";
import { WaveView } from "../components/WaveView";
import { LEVEL_LABELS, STATUS_LABELS } from "../content/labels";
import { type SaveFn, type SaveStatus, useAutosave } from "../hooks/useAutosave";
import { useRunEvents } from "../hooks/useRunEvents";

type LoadState =
  | { kind: "loading" }
  | { kind: "ok"; detail: ExerciseDetail }
  | { kind: "error"; message: string };

type Tab = "tests" | "log" | "wave";

const NO_DIAGNOSTICS: EditorDiagnostic[] = [];

export function ExercisePage() {
  const { exerciseId = "" } = useParams();
  // A new exercise gets a fresh view (code, run, tabs).
  return <ExerciseView key={exerciseId} exerciseId={exerciseId} />;
}

function ExerciseView({ exerciseId }: { exerciseId: string }) {
  const [load, setLoad] = useState<LoadState>({ kind: "loading" });
  const [code, setCode] = useState<string | null>(null);
  const [run, setRun] = useState<ExerciseRun | null>(null);
  const [pendingRunId, setPendingRunId] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [elapsedMs, setElapsedMs] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("tests");
  const events = useRunEvents(pendingRunId);

  const saveDraft = useCallback<SaveFn>(
    async (value, { keepalive }) => {
      const { response } = await api.PUT("/api/exercises/{exercise_id}/code", {
        params: { path: { exercise_id: exerciseId } },
        body: { code: value },
        keepalive,
      });
      if (!response.ok) throw new Error(httpErrorMessage(response.status));
    },
    [exerciseId],
  );
  const autosave = useAutosave(saveDraft);

  /** Every user edit goes through here (typing, reset); loading the page does not. */
  const editCode = useCallback(
    (value: string) => {
      setCode(value);
      autosave.schedule(value);
    },
    [autosave],
  );

  /** Load the exercise; the first load also fills the editor and the last result. */
  const fetchDetail = useCallback(
    (initial: boolean) => {
      api
        .GET("/api/exercises/{exercise_id}", { params: { path: { exercise_id: exerciseId } } })
        .then(
          ({ data, response }) => {
            if (!data) {
              const message =
                response.status === 404 ? "Soal tidak ditemukan." : httpErrorMessage(response.status);
              setLoad({ kind: "error", message });
              return;
            }
            setLoad({ kind: "ok", detail: data });
            if (initial) {
              setCode(data.code);
              const last = data.last_run;
              if (last && TERMINAL_STATUSES.has(last.status)) setRun(last);
              else if (last) setPendingRunId(last.id); // still running: follow it
            }
          },
          () => setLoad({ kind: "error", message: UNREACHABLE }),
        );
    },
    [exerciseId],
  );

  useEffect(() => {
    fetchDetail(true);
  }, [fetchDetail]);

  // When the stream reports a final status, fetch the graded result.
  useEffect(() => {
    if (pendingRunId === null || events.status === null) return;
    if (!TERMINAL_STATUSES.has(events.status)) return;
    let cancelled = false;
    api
      .GET("/api/exercises/{exercise_id}/runs/{run_id}", {
        params: { path: { exercise_id: exerciseId, run_id: pendingRunId } },
      })
      .then(
        ({ data, response }) => {
          if (cancelled) return;
          if (data) setRun(data);
          else setActionError(`Gagal membaca hasil run. ${httpErrorMessage(response.status)}`);
          if (startedAt !== null) setElapsedMs(performance.now() - startedAt);
          setPendingRunId(null);
          fetchDetail(false); // attempts, status and solution availability changed
        },
        () => {
          if (!cancelled) setActionError(UNREACHABLE);
        },
      );
    return () => {
      cancelled = true;
    };
  }, [events.status, pendingRunId, exerciseId, startedAt, fetchDetail]);

  const running = pendingRunId !== null;

  /** `editorCode` is what the editor shows right now (Ctrl+Enter); it wins over state. */
  const startRun = useCallback(
    async (editorCode?: string) => {
      const source = editorCode ?? code;
      if (source === null || running) return;
      if (editorCode !== undefined) setCode(editorCode);
      setActionError(null);
      setRun(null);
      setElapsedMs(null);
      setStartedAt(performance.now());
      try {
        const { data, response } = await api.POST("/api/exercises/{exercise_id}/runs", {
          params: { path: { exercise_id: exerciseId } },
          body: { code: source },
        });
        if (data) setPendingRunId(data.id);
        else setActionError(`Gagal menjalankan. ${httpErrorMessage(response.status)}`);
      } catch {
        setActionError(UNREACHABLE);
      }
    },
    [code, running, exerciseId],
  );

  if (load.kind === "loading") return <p className="text-sm text-slate-500">Memuat soal…</p>;
  if (load.kind === "error") {
    return (
      <div className="flex flex-col gap-2">
        <BackLink />
        <p className="text-sm text-red-700">{load.message}</p>
      </div>
    );
  }

  const { detail } = load;
  const diagnostics =
    run?.grade?.status === "compile_error" ? run.grade.diagnostics : NO_DIAGNOSTICS;

  return (
    // Side by side on wide screens; stacked (statement first) on narrow ones.
    <div className="flex flex-col gap-4 lg:grid lg:h-[calc(100vh-4rem)] lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <StatementPane detail={detail} />

      <div className="flex min-h-0 flex-col gap-3">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => void startRun()}
            disabled={running || code === null}
            title="Ctrl+Enter"
            className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            Run
          </button>
          <span className="text-xs text-slate-500">Ctrl+Enter</span>
          <SaveIndicator status={autosave.status} />
          <button
            type="button"
            onClick={() => editCode(detail.starter)}
            className="ml-auto rounded-md border border-slate-300 px-3 py-1.5 text-sm"
          >
            Reset ke starter
          </button>
        </div>
        {actionError && <p className="text-sm text-red-700">{actionError}</p>}

        <div className="h-96 overflow-hidden rounded-lg border border-slate-200 bg-white lg:h-auto lg:min-h-64 lg:flex-1">
          {code !== null && (
            <CodeEditor
              value={code}
              onChange={editCode}
              onRun={(current) => void startRun(current)}
              diagnostics={diagnostics}
              language={detail.language}
            />
          )}
        </div>

        <ResultPanel
          run={run}
          running={running}
          liveStatus={events.status}
          liveLines={events.lines}
          elapsedMs={elapsedMs}
          tab={tab}
          onTab={setTab}
        />
      </div>
    </div>
  );
}

function SaveIndicator({ status }: { status: SaveStatus }) {
  switch (status) {
    case "pending":
    case "saving":
      return <span className="text-xs text-slate-500">Menyimpan…</span>;
    case "saved":
      return <span className="text-xs text-slate-500">Tersimpan</span>;
    case "error":
      return (
        <span className="text-xs text-red-700">
          Gagal menyimpan. Dicoba lagi saat Anda mengetik.
        </span>
      );
    default:
      return null;
  }
}

function BackLink() {
  return (
    <Link to="/latihan" className="text-sm text-slate-600 hover:underline">
      ← Daftar soal
    </Link>
  );
}

/** README files start with "# Title"; the page already shows the title from exercise.yaml. */
function withoutLeadingTitle(markdown: string): string {
  return markdown.replace(/^\s*# [^\n]*\n+/, "");
}

function StatementPane({ detail }: { detail: ExerciseDetail }) {
  return (
    <div className="flex min-h-0 flex-col gap-4 rounded-lg border border-slate-200 bg-white p-5 lg:overflow-auto">
      <div>
        <BackLink />
        <h1 className="mt-2 text-xl font-semibold">{detail.title}</h1>
        <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-600">
          <span>{LEVEL_LABELS[detail.level] ?? `Level ${detail.level}`}</span>
          <span>·</span>
          <span>{STATUS_LABELS[detail.status]}</span>
          {detail.attempts > 0 && (
            <>
              <span>·</span>
              <span>{detail.attempts} percobaan</span>
            </>
          )}
        </div>
      </div>
      <Markdown>{withoutLeadingTitle(detail.statement)}</Markdown>
      <Hints exerciseId={detail.id} initial={detail.hints} total={detail.hints_total} />
      <Solution detail={detail} />
    </div>
  );
}

function Hints({ exerciseId, initial, total }: { exerciseId: string; initial: string[]; total: number }) {
  const [hints, setHints] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  if (total === 0) return null;

  async function openNext() {
    try {
      const { data, response } = await api.POST("/api/exercises/{exercise_id}/hints/next", {
        params: { path: { exercise_id: exerciseId } },
      });
      if (data) setHints(data.hints);
      else setError(httpErrorMessage(response.status));
    } catch {
      setError(UNREACHABLE);
    }
  }

  return (
    <section className="border-t border-slate-100 pt-4">
      <h2 className="mb-2 text-sm font-semibold">Petunjuk</h2>
      {hints.length > 0 && (
        <ol className="mb-3 list-decimal space-y-1 pl-5 text-sm">
          {hints.map((hint) => (
            <li key={hint}>{hint}</li>
          ))}
        </ol>
      )}
      {hints.length < total && (
        <button
          type="button"
          onClick={() => void openNext()}
          className="rounded-md border border-slate-300 px-3 py-1 text-sm"
        >
          Buka petunjuk ({hints.length}/{total})
        </button>
      )}
      {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
    </section>
  );
}

function Solution({ detail }: { detail: ExerciseDetail }) {
  const [code, setCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function show() {
    try {
      const { data, response } = await api.GET("/api/exercises/{exercise_id}/solution", {
        params: { path: { exercise_id: detail.id } },
      });
      if (data) setCode(data.code);
      else setError(httpErrorMessage(response.status));
    } catch {
      setError(UNREACHABLE);
    }
  }

  return (
    <section className="border-t border-slate-100 pt-4">
      <h2 className="mb-2 text-sm font-semibold">Solusi</h2>
      {!detail.solution_available && (
        <p className="text-sm text-slate-600">
          Solusi terbuka setelah lulus atau setelah {detail.solution_unlock_attempts} percobaan
          (sekarang {detail.attempts}).
        </p>
      )}
      {detail.solution_available && code === null && (
        <button
          type="button"
          onClick={() => void show()}
          className="rounded-md border border-slate-300 px-3 py-1 text-sm"
        >
          Lihat solusi
        </button>
      )}
      {code !== null && (
        <pre className="overflow-auto rounded-md bg-slate-900 p-3 text-xs text-slate-100">{code}</pre>
      )}
      {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
    </section>
  );
}

function verdict(grade: GradeResult): { text: string; tone: "ok" | "bad" } {
  const total = grade.tests.length;
  const failed = grade.tests.filter((t) => !t.passed).length;
  switch (grade.status) {
    case "pass":
      return { text: `Lulus semua test (${total}/${total})`, tone: "ok" };
    case "fail":
      return { text: `${failed} dari ${total} test gagal`, tone: "bad" };
    case "compile_error":
      return { text: "Kode tidak bisa dikompilasi", tone: "bad" };
    default:
      return { text: "Grader gagal menjalankan test (lihat Log)", tone: "bad" };
  }
}

function formatSeconds(ms: number): string {
  return `${(ms / 1000).toLocaleString("id-ID", { maximumFractionDigits: 1 })} detik`;
}

function ResultPanel(props: {
  run: ExerciseRun | null;
  running: boolean;
  liveStatus: string | null;
  liveLines: string[];
  elapsedMs: number | null;
  tab: Tab;
  onTab: (tab: Tab) => void;
}) {
  const { run, running, liveStatus, liveLines, elapsedMs, tab, onTab } = props;
  const grade = run?.grade ?? null;
  const ids = { tests: useId(), log: useId(), wave: useId() };

  // Once opened, the waveform viewer stays mounted so switching tabs does not reload Surfer.
  const [waveOpened, setWaveOpened] = useState(tab === "wave");
  function selectTab(next: Tab) {
    if (next === "wave") setWaveOpened(true);
    onTab(next);
  }
  // While a new run is going, keep showing the previous waveform instead of an empty panel.
  const [lastWave, setLastWave] = useState<string | null>(null);
  const currentWave = grade?.wave_url ?? null;
  if (currentWave !== null && currentWave !== lastWave) setLastWave(currentWave);
  const waveUrl = running ? lastWave : currentWave;

  let header: React.ReactNode = (
    <span className="text-slate-500">Belum ada hasil. Tekan Run untuk menguji kode.</span>
  );
  if (running) {
    header = (
      <span className="text-slate-600">
        {liveStatus === "queued" ? "Menunggu giliran…" : "Menjalankan…"}
      </span>
    );
  } else if (grade) {
    const v = verdict(grade);
    header = (
      <span className={v.tone === "ok" ? "font-medium text-green-700" : "font-medium text-red-700"}>
        {v.text}
      </span>
    );
  } else if (run) {
    header = <span className="font-medium text-red-700">{run.error ?? "Run gagal."}</span>;
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: "tests", label: "Tests" },
    { id: "log", label: "Log" },
    { id: "wave", label: "Waveform" },
  ];

  return (
    <section
      className={`flex shrink-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white ${
        tab === "wave" ? "h-[32rem]" : "h-72"
      }`}
    >
      <div className="flex items-center gap-4 border-b border-slate-100 px-4 py-2 text-sm">
        <div className="flex min-w-0 flex-1 items-baseline gap-2">
          <span className="truncate">{header}</span>
          {elapsedMs !== null && !running && (
            <span className="shrink-0 text-xs text-slate-500">· {formatSeconds(elapsedMs)}</span>
          )}
        </div>
        <div role="tablist" className="flex shrink-0 gap-1">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              id={`${ids[t.id]}-tab`}
              aria-controls={ids[t.id]}
              aria-selected={tab === t.id}
              onClick={() => selectTab(t.id)}
              className={`rounded px-2 py-1 text-xs ${
                tab === t.id ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
      <div
        role="tabpanel"
        id={ids[tab]}
        aria-labelledby={`${ids[tab]}-tab`}
        className="min-h-0 flex-1 overflow-auto p-3 text-sm"
      >
        {tab === "tests" && <TestsTab grade={grade} />}
        {tab === "log" && (
          <pre className="font-mono text-xs whitespace-pre-wrap text-slate-700">
            {running ? liveLines.join("\n") : grade?.log || run?.error || "Belum ada log."}
          </pre>
        )}
        {waveOpened && (
          <div className={tab === "wave" ? "h-full" : "hidden"}>
            <WaveTab url={waveUrl} />
          </div>
        )}
      </div>
    </section>
  );
}

function TestsTab({ grade }: { grade: GradeResult | null }) {
  if (!grade) return null;
  if (grade.status === "compile_error") {
    return (
      <ul aria-label="Error kompilasi" className="space-y-1 font-mono text-xs">
        {grade.diagnostics.map((d) => (
          <li key={`${d.line}-${d.message}`} className="text-red-700">
            Baris {d.line}: {d.message}
          </li>
        ))}
        {grade.diagnostics.length === 0 && <li>Lihat tab Log untuk pesan compiler.</li>}
      </ul>
    );
  }
  return (
    <ul aria-label="Hasil test" className="space-y-2">
      {grade.tests.map((t) => (
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
  );
}

function WaveTab({ url }: { url: string | null }) {
  if (!url) {
    return <p className="text-slate-500">Belum ada waveform. Jalankan kode sampai simulasi selesai.</p>;
  }
  return <WaveView url={url} />;
}
