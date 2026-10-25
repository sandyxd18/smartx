import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router";
import {
  api,
  type ProjectDetail,
  type ProjectDiagnostic,
  type ProjectEntry,
  type Snippet,
} from "../api/client";
import { apiErrorMessage, httpErrorMessage, UNREACHABLE } from "../api/errors";
import { CodeEditor } from "../components/CodeEditor";
import { ConfigEditor } from "../components/ConfigEditor";
import type { EditorDiagnostic } from "../components/codeEditorTypes";
import { FileTree } from "../components/FileTree";
import { LessonsPanel } from "../components/LessonsPanel";
import { RunPanel, type RunTab } from "../components/RunPanel";
import { SaveIndicator } from "../components/SaveIndicator";
import { languageForPath } from "../editor/languages";
import { applySnippet } from "../editor/snippets";
import { type SaveFn, useAutosave } from "../hooks/useAutosave";
import { projectProblems, useProjectRun } from "../hooks/useProjectRun";

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ok"; detail: ProjectDetail };

/** The file in the editor. `id` changes only when another file is opened (not on rename). */
interface OpenFile {
  id: number;
  path: string;
  content: string;
}

interface Draft {
  path: string;
  content: string;
}

const CONFIG_PATH = "smartx.yaml";

function within(path: string, folder: string): boolean {
  return path === folder || path.startsWith(`${folder}/`);
}

export function ProjectPage() {
  const { projectId = "" } = useParams();
  return <ProjectView key={projectId} projectId={Number(projectId)} />;
}

function ProjectView({ projectId }: { projectId: number }) {
  const [load, setLoad] = useState<LoadState>({ kind: "loading" });
  const [selected, setSelected] = useState<string | null>(null);
  const [open, setOpen] = useState<OpenFile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const openCounter = useRef(0);

  const saveFile = useCallback<SaveFn<Draft>>(
    async ({ path, content }, { keepalive }) => {
      const { response } = await api.PUT(
        "/api/projects/{project_id}/files/{path}",
        {
          params: { path: { project_id: projectId, path } },
          body: { content },
          keepalive,
        },
      );
      if (!response.ok) throw new Error(httpErrorMessage(response.status));
    },
    [projectId],
  );
  const autosave = useAutosave(saveFile);
  const { settle: settleText } = autosave;
  // The config form saves on its own; every tree change waits for it too.
  const formSettle = useRef<(() => Promise<void>) | null>(null);
  const settle = useCallback(async () => {
    await formSettle.current?.();
    await settleText();
  }, [settleText]);
  const registerFormSettle = useCallback((fn: (() => Promise<void>) | null) => {
    formSettle.current = fn;
  }, []);
  // Lint copies the saved files, so pending edits are stored first.
  const lint = useProjectRun(projectId, settle);
  const sim = useProjectRun(projectId, settle);
  const [runTab, setRunTab] = useState<RunTab>("problems");
  const [showLessons, setShowLessons] = useState(false);
  // A simulation that did not compile is explained in Problems; switch there once.
  const [shownCompileError, setShownCompileError] = useState<string | null>(
    null,
  );
  const simRun = sim.run;
  if (
    simRun?.sim?.status === "compile_error" &&
    shownCompileError !== simRun.id
  ) {
    setShownCompileError(simRun.id);
    setRunTab("problems");
  }
  const [reveal, setReveal] = useState<{ line: number; column: number } | null>(
    null,
  );

  const showSavedConfig = useCallback((text: string) => {
    setOpen((current) => current && { ...current, content: text });
  }, []);

  // cocotb snippets for the "Sisipkan snippet" menu of Python files.
  const [snippets, setSnippets] = useState<Snippet[]>([]);
  useEffect(() => {
    api.GET("/api/snippets").then(
      ({ data }) => setSnippets(data ?? []),
      () => undefined, // the editor works without them
    );
  }, []);

  const refresh = useCallback(
    () =>
      api
        .GET("/api/projects/{project_id}", {
          params: { path: { project_id: projectId } },
        })
        .then(
          ({ data, response }) => {
            if (data) {
              setLoad({ kind: "ok", detail: data });
              return;
            }
            const message =
              response.status === 404
                ? "Proyek tidak ditemukan."
                : httpErrorMessage(response.status);
            setLoad({ kind: "error", message });
          },
          () => setLoad({ kind: "error", message: UNREACHABLE }),
        ),
    [projectId],
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  /** Store pending edits, then load another file into the editor. */
  const openFile = useCallback(
    async (path: string) => {
      setSelected(path);
      await settle();
      try {
        const {
          data,
          error: apiError,
          response,
        } = await api.GET("/api/projects/{project_id}/files/{path}", {
          params: { path: { project_id: projectId, path } },
        });
        if (!data) {
          setError(apiErrorMessage(apiError, response.status));
          return;
        }
        openCounter.current += 1;
        setReveal(null);
        setOpen({
          id: openCounter.current,
          path: data.path,
          content: data.content,
        });
        setError(null);
      } catch {
        setError(UNREACHABLE);
      }
    },
    [projectId, settle],
  );

  const openPath = open?.path ?? null;
  const markers = useMemo<EditorDiagnostic[]>(
    () =>
      projectProblems(lint, sim)
        .filter((d) => d.file === openPath)
        .map((d) => ({
          line: d.line,
          column: d.col ?? null,
          endColumn: d.end_col ?? null,
          severity: d.severity,
          code: d.code,
          message: d.message,
        })),
    [lint, sim, openPath],
  );

  async function openRun(runId: string) {
    try {
      const {
        data,
        error: apiError,
        response,
      } = await api.GET("/api/projects/{project_id}/runs/{run_id}", {
        params: { path: { project_id: projectId, run_id: runId } },
      });
      if (!data) {
        setError(apiErrorMessage(apiError, response.status));
        return;
      }
      if (data.kind === "lint") {
        lint.show(data);
        setRunTab("problems");
      } else {
        sim.show(data);
        setRunTab("tests");
      }
    } catch {
      setError(UNREACHABLE);
    }
  }

  async function openProblem(d: ProjectDiagnostic) {
    if (d.file !== openPath) await openFile(d.file);
    setReveal({ line: d.line, column: d.col ?? 1 });
  }

  function edit(content: string) {
    if (!open) return;
    setOpen({ ...open, content });
    autosave.schedule({ path: open.path, content });
  }

  function insertSnippet(id: string) {
    const snippet = snippets.find((s) => s.id === id);
    if (!open || !snippet) return;
    const result = applySnippet(open.content, snippet);
    edit(result.content);
    setReveal({ line: result.line, column: 1 });
  }

  async function create(
    kind: ProjectEntry["kind"],
    path: string,
  ): Promise<boolean> {
    await settle();
    try {
      const { error: apiError, response } =
        kind === "file"
          ? await api.POST("/api/projects/{project_id}/files", {
              params: { path: { project_id: projectId } },
              body: { path, content: "" },
            })
          : await api.POST("/api/projects/{project_id}/folders", {
              params: { path: { project_id: projectId } },
              body: { path },
            });
      if (!response.ok) {
        setError(apiErrorMessage(apiError, response.status));
        return false;
      }
    } catch {
      setError(UNREACHABLE);
      return false;
    }
    setError(null);
    await refresh();
    if (kind === "file") await openFile(path);
    else setSelected(path);
    return true;
  }

  async function rename(from: string, to: string): Promise<boolean> {
    await settle();
    try {
      const { error: apiError, response } = await api.POST(
        "/api/projects/{project_id}/move",
        {
          params: { path: { project_id: projectId } },
          body: { from_path: from, to_path: to },
        },
      );
      if (!response.ok) {
        setError(apiErrorMessage(apiError, response.status));
        return false;
      }
    } catch {
      setError(UNREACHABLE);
      return false;
    }
    setError(null);
    const moved = (path: string) =>
      within(path, from) ? to + path.slice(from.length) : path;
    setOpen((current) => current && { ...current, path: moved(current.path) });
    setSelected((current) => current && moved(current));
    await refresh();
    return true;
  }

  async function remove(entry: ProjectEntry) {
    const question =
      entry.kind === "dir"
        ? `Hapus folder ${entry.path} beserta seluruh isinya?`
        : `Hapus file ${entry.path}?`;
    if (!window.confirm(question)) return;
    // Store pending edits first, so a late autosave cannot bring the file back.
    await settle();
    try {
      const { error: apiError, response } = await api.DELETE(
        "/api/projects/{project_id}/files/{path}",
        { params: { path: { project_id: projectId, path: entry.path } } },
      );
      if (!response.ok) {
        setError(apiErrorMessage(apiError, response.status));
        return;
      }
    } catch {
      setError(UNREACHABLE);
      return;
    }
    setError(null);
    setOpen((current) =>
      current && within(current.path, entry.path) ? null : current,
    );
    setSelected((current) =>
      current && within(current, entry.path) ? null : current,
    );
    await refresh();
  }

  if (load.kind === "loading")
    return <p className="text-sm text-slate-500">Memuat proyek…</p>;
  if (load.kind === "error") {
    return (
      <div className="flex flex-col gap-2">
        <BackLink />
        <p className="text-sm text-red-700">{load.message}</p>
      </div>
    );
  }

  return (
    <section className="flex flex-col gap-3 lg:h-[calc(100vh-4rem)]">
      <div className="flex flex-col gap-1">
        <BackLink />
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold">{load.detail.name}</h1>
          <SaveIndicator status={autosave.status} />
          <button
            type="button"
            aria-pressed={showLessons}
            onClick={() => setShowLessons((shown) => !shown)}
            className="ml-auto rounded-md border border-slate-300 px-3 py-1.5 text-sm aria-pressed:bg-slate-100"
          >
            Materi
          </button>
          <button
            type="button"
            onClick={() => {
              setRunTab("problems");
              void lint.start("lint");
            }}
            disabled={lint.running}
            title="verilator --lint-only -Wall atas file sumber di smartx.yaml"
            className="rounded-md border border-slate-300 px-4 py-1.5 text-sm font-medium disabled:opacity-50"
          >
            Lint
          </button>
          <button
            type="button"
            onClick={() => {
              setRunTab("tests");
              void sim.start("sim");
            }}
            disabled={sim.running}
            title="Jalankan testbench cocotb di smartx.yaml dengan simulator yang dipilih"
            className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            Simulasi
          </button>
        </div>
        {error && <p className="text-sm text-red-700">{error}</p>}
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-3 lg:flex-row">
        <aside className="overflow-auto rounded-lg border border-slate-200 bg-white p-2 lg:w-64 lg:shrink-0">
          <FileTree
            entries={load.detail.entries}
            selected={selected}
            onSelect={(entry) => {
              if (entry.kind === "file") void openFile(entry.path);
              else setSelected(entry.path);
            }}
            onCreate={create}
            onRename={rename}
            onDelete={(entry) => void remove(entry)}
          />
        </aside>

        <div className="flex min-h-96 flex-1 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white">
          {open?.path === CONFIG_PATH ? (
            <div className="min-h-0 flex-1" key={open.id}>
              <ConfigEditor
                projectId={projectId}
                text={open.content}
                pyFiles={load.detail.entries
                  .filter((e) => e.kind === "file" && e.path.endsWith(".py"))
                  .map((e) => e.path)}
                onEdit={edit}
                onSaved={showSavedConfig}
                settleText={settleText}
                registerSettle={registerFormSettle}
              />
            </div>
          ) : open ? (
            <>
              <div className="flex items-center gap-3 border-b border-slate-200 px-3 py-1.5 text-xs">
                <span className="font-mono text-slate-600">{open.path}</span>
                {open.path.endsWith(".py") && snippets.length > 0 && (
                  <select
                    aria-label="Sisipkan snippet"
                    value=""
                    onChange={(e) => insertSnippet(e.target.value)}
                    className="ml-auto rounded border border-slate-300 px-1 py-0.5"
                  >
                    <option value="">Sisipkan snippet cocotb…</option>
                    {snippets.map((s) => (
                      <option key={s.id} value={s.id} title={s.description}>
                        {s.title}
                      </option>
                    ))}
                  </select>
                )}
              </div>
              <div className="min-h-0 flex-1" key={open.id}>
                <CodeEditor
                  value={open.content}
                  onChange={edit}
                  language={languageForPath(open.path)}
                  diagnostics={markers}
                  reveal={reveal}
                />
              </div>
            </>
          ) : (
            <p className="p-4 text-sm text-slate-500">
              Pilih file di kiri untuk mulai mengedit.
            </p>
          )}
        </div>

        {showLessons && <LessonsPanel step={2} />}
      </div>

      <RunPanel
        projectId={projectId}
        lint={lint}
        sim={sim}
        tab={runTab}
        onTab={setRunTab}
        onOpen={(d) => void openProblem(d)}
        onOpenRun={(id) => void openRun(id)}
      />
    </section>
  );
}

function BackLink() {
  return (
    <Link to="/workspace" className="text-sm text-slate-600 hover:underline">
      ← Semua proyek
    </Link>
  );
}
