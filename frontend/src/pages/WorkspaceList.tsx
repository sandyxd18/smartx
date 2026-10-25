import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import {
  api,
  type ExerciseSummary,
  type ProjectSummary,
  type ProjectTemplate,
} from "../api/client";
import { apiErrorMessage, httpErrorMessage, UNREACHABLE } from "../api/errors";
import { groupByTopic } from "../content/labels";

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ok"; projects: ProjectSummary[] };

const DATE = new Intl.DateTimeFormat("id-ID", { dateStyle: "medium", timeStyle: "short" });

export function WorkspaceList() {
  const [load, setLoad] = useState<LoadState>({ kind: "loading" });
  const [templates, setTemplates] = useState<ProjectTemplate[]>([]);
  const [exercises, setExercises] = useState<ExerciseSummary[]>([]);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchProjects = useCallback(() => {
    api.GET("/api/projects").then(
      ({ data, response }) =>
        setLoad(
          data
            ? { kind: "ok", projects: data }
            : { kind: "error", message: httpErrorMessage(response.status) },
        ),
      () => setLoad({ kind: "error", message: UNREACHABLE }),
    );
  }, []);

  useEffect(() => {
    fetchProjects();
    // Only for the "start from" choices; the page still works without them.
    api.GET("/api/project-templates").then(
      ({ data }) => setTemplates(data ?? []),
      () => undefined,
    );
    api.GET("/api/exercises").then(
      ({ data }) => setExercises(data ?? []),
      () => undefined,
    );
  }, [fetchProjects]);

  async function remove(project: ProjectSummary) {
    if (!window.confirm(`Hapus proyek "${project.name}" beserta semua file dan riwayat run-nya?`)) {
      return;
    }
    setActionError(null);
    try {
      const { error, response } = await api.DELETE("/api/projects/{project_id}", {
        params: { path: { project_id: project.id } },
      });
      if (!response.ok) setActionError(apiErrorMessage(error, response.status));
    } catch {
      setActionError(UNREACHABLE);
    }
    fetchProjects();
  }

  return (
    <section className="flex max-w-3xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Workspace</h1>
        <p className="mt-1 text-sm text-slate-600">
          Proyek bebas dengan banyak file dan testbench buatanmu sendiri.
        </p>
      </div>

      <NewProjectForm templates={templates} exercises={exercises} />

      <div className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold">Proyek</h2>
        {actionError && <p className="text-sm text-red-700">{actionError}</p>}
        {load.kind === "loading" && <p className="text-sm text-slate-500">Memuat proyek…</p>}
        {load.kind === "error" && <p className="text-sm text-red-700">{load.message}</p>}
        {load.kind === "ok" && load.projects.length === 0 && (
          <p className="text-sm text-slate-500">Belum ada proyek. Buat satu di atas.</p>
        )}
        {load.kind === "ok" && load.projects.length > 0 && (
          <ul aria-label="Daftar proyek" className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {load.projects.map((p) => (
              <li key={p.id} className="flex items-center gap-4 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <Link to={`/workspace/${p.id}`} className="font-medium hover:underline">
                    {p.name}
                  </Link>
                  <div className="text-xs text-slate-500">
                    {sourceLabel(p.source, templates, exercises)} · {p.file_count} file · diubah{" "}
                    {DATE.format(new Date(p.updated_at))}
                  </div>
                </div>
                <button
                  type="button"
                  aria-label={`Hapus proyek ${p.name}`}
                  onClick={() => void remove(p)}
                  className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-600 hover:border-red-300 hover:text-red-700"
                >
                  Hapus
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function sourceLabel(
  source: string | null,
  templates: ProjectTemplate[],
  exercises: ExerciseSummary[],
): string {
  if (!source) return "Proyek";
  const [kind, id] = source.split(":", 2);
  if (kind === "template") {
    return `Template: ${templates.find((t) => t.id === id)?.title ?? id}`;
  }
  if (kind === "exercise") {
    return `Dari soal: ${exercises.find((e) => e.id === id)?.title ?? id}`;
  }
  return source;
}

function NewProjectForm(props: { templates: ProjectTemplate[]; exercises: ExerciseSummary[] }) {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [start, setStart] = useState("template:empty");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const chosenTemplate = props.templates.find((t) => `template:${t.id}` === start);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const [kind, id] = start.split(":", 2);
    const body = kind === "exercise" ? { name, exercise_id: id } : { name, template: id };
    try {
      const { data, error: apiError, response } = await api.POST("/api/projects", { body });
      if (data) {
        void navigate(`/workspace/${data.id}`);
        return;
      }
      setError(apiErrorMessage(apiError, response.status));
    } catch {
      setError(UNREACHABLE);
    }
    setBusy(false);
  }

  return (
    <form
      onSubmit={(e) => void submit(e)}
      className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4"
    >
      <h2 className="text-lg font-semibold">Proyek baru</h2>
      <div className="flex flex-wrap gap-3">
        <label className="flex min-w-48 flex-1 flex-col gap-1 text-sm">
          Nama proyek
          <input
            required
            maxLength={80}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="misalnya: FIFO sinkron"
            className="rounded-md border border-slate-300 px-2 py-1"
          />
        </label>
        <label className="flex min-w-48 flex-1 flex-col gap-1 text-sm">
          Mulai dari
          <select
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="rounded-md border border-slate-300 px-2 py-1"
          >
            {props.templates.length === 0 && <option value="template:empty">Kosong</option>}
            {props.templates.map((t) => (
              <option key={t.id} value={`template:${t.id}`}>
                {t.title}
              </option>
            ))}
            {groupByTopic(props.exercises).map((group) => (
              <optgroup key={group.topic} label={`Salin dari soal: ${group.label}`}>
                {group.exercises.map((ex) => (
                  <option key={ex.id} value={`exercise:${ex.id}`}>
                    {ex.title}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>
      </div>
      <p className="text-xs text-slate-500">
        {chosenTemplate
          ? chosenTemplate.description
          : start.startsWith("exercise:")
            ? "Menyalin kode terakhirmu (atau starter), testbench, dan teks soal. Solusi tidak ikut."
            : ""}
      </p>
      {error && <p className="text-sm text-red-700">{error}</p>}
      <div>
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50"
        >
          Buat proyek
        </button>
      </div>
    </form>
  );
}
