import { useEffect, useId, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { api, type ExerciseStatus, type ExerciseSummary } from "../api/client";
import { httpErrorMessage, UNREACHABLE } from "../api/errors";
import { groupByTopic, LEVEL_LABELS, STATUS_LABELS } from "../content/labels";

type LoadState =
  | { kind: "loading" }
  | { kind: "ok"; exercises: ExerciseSummary[] }
  | { kind: "error"; message: string };

const STATUS_COLORS: Record<ExerciseStatus, string> = {
  not_started: "bg-slate-100 text-slate-600",
  attempted: "bg-amber-100 text-amber-800",
  solved: "bg-green-100 text-green-800",
};

const LEVEL_COLORS: Record<number, string> = {
  1: "border-sky-200 text-sky-700",
  2: "border-violet-200 text-violet-700",
  3: "border-rose-200 text-rose-700",
};

function useExercises(): LoadState {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  useEffect(() => {
    let cancelled = false;
    api.GET("/api/exercises").then(
      ({ data, response }) => {
        if (cancelled) return;
        setState(
          data
            ? { kind: "ok", exercises: data }
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
  }, []);
  return state;
}

function matches(exercise: ExerciseSummary, query: string, status: string, level: string) {
  const q = query.trim().toLowerCase();
  return (
    (status === "all" || exercise.status === status) &&
    (level === "all" || String(exercise.level) === level) &&
    (q === "" || exercise.title.toLowerCase().includes(q) || exercise.id.includes(q))
  );
}

function ExerciseRow({ exercise }: { exercise: ExerciseSummary }) {
  return (
    <li>
      <Link
        to={`/latihan/${exercise.id}`}
        className="flex items-center gap-3 px-4 py-3 hover:bg-slate-50"
      >
        <div className="min-w-0 flex-1">
          <div className="truncate font-medium" title={exercise.title}>
            {exercise.title}
          </div>
          {exercise.requires.length > 0 && (
            <div className="text-xs text-slate-500">
              Prasyarat: {exercise.requires.join(", ")}
            </div>
          )}
        </div>
        {exercise.attempts > 0 && (
          <span className="text-xs text-slate-500">{exercise.attempts} percobaan</span>
        )}
        <span
          className={`rounded-full border px-2 py-0.5 text-xs ${LEVEL_COLORS[exercise.level] ?? ""}`}
        >
          {LEVEL_LABELS[exercise.level] ?? `Level ${exercise.level}`}
        </span>
        <span
          className={`w-14 rounded-full px-2 py-0.5 text-center text-xs font-medium ${STATUS_COLORS[exercise.status]}`}
        >
          {STATUS_LABELS[exercise.status]}
        </span>
      </Link>
    </li>
  );
}

function TopicSection({ label, exercises }: { label: string; exercises: ExerciseSummary[] }) {
  const id = useId();
  return (
    <section aria-labelledby={id}>
      <h2 className="mb-2 flex items-baseline gap-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
        <span id={id}>{label}</span>
        <span className="font-normal normal-case text-slate-400">{exercises.length}</span>
      </h2>
      <ul className="divide-y divide-slate-100 overflow-hidden rounded-lg border border-slate-200 bg-white">
        {exercises.map((exercise) => (
          <ExerciseRow key={exercise.id} exercise={exercise} />
        ))}
      </ul>
    </section>
  );
}

export function ExerciseList() {
  const state = useExercises();
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "";
  const status = params.get("status") ?? "all";
  const level = params.get("level") ?? "all";

  // Filters live in the URL so a refresh or a shared link keeps them.
  function setFilter(key: string, value: string, empty: string) {
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (value === empty) next.delete(key);
        else next.set(key, value);
        return next;
      },
      { replace: true },
    );
  }

  return (
    <div className="flex max-w-4xl flex-col gap-6">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-2xl font-semibold">Latihan</h1>
        {state.kind === "ok" && state.exercises.length > 0 && (
          <p className="text-sm text-slate-600">
            {state.exercises.filter((e) => e.status === "solved").length} dari{" "}
            {state.exercises.length} soal lulus
          </p>
        )}
      </header>

      <div className="flex flex-wrap items-end gap-3 text-sm">
        <label className="flex flex-1 flex-col gap-1">
          <span className="text-slate-600">Cari</span>
          <input
            type="search"
            value={query}
            onChange={(e) => setFilter("q", e.target.value, "")}
            placeholder="Judul atau id soal"
            className="rounded-md border border-slate-300 px-3 py-1.5"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-slate-600">Status</span>
          <select
            value={status}
            onChange={(e) => setFilter("status", e.target.value, "all")}
            className="rounded-md border border-slate-300 bg-white px-2 py-1.5"
          >
            <option value="all">Semua</option>
            <option value="not_started">{STATUS_LABELS.not_started}</option>
            <option value="attempted">{STATUS_LABELS.attempted}</option>
            <option value="solved">{STATUS_LABELS.solved}</option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-slate-600">Level</span>
          <select
            value={level}
            onChange={(e) => setFilter("level", e.target.value, "all")}
            className="rounded-md border border-slate-300 bg-white px-2 py-1.5"
          >
            <option value="all">Semua</option>
            {[1, 2, 3].map((l) => (
              <option key={l} value={String(l)}>
                {LEVEL_LABELS[l]}
              </option>
            ))}
          </select>
        </label>
      </div>

      {state.kind === "loading" && <p className="text-sm text-slate-500">Memuat soal…</p>}
      {state.kind === "error" && <p className="text-sm text-red-700">{state.message}</p>}
      {state.kind === "ok" && <Groups exercises={state.exercises} filter={{ query, status, level }} />}
    </div>
  );
}

function Groups({
  exercises,
  filter,
}: {
  exercises: ExerciseSummary[];
  filter: { query: string; status: string; level: string };
}) {
  if (exercises.length === 0) {
    return (
      <p className="text-sm text-slate-600">
        Belum ada soal. Tambahkan soal di <code>content/exercises/</code>.
      </p>
    );
  }
  const visible = exercises.filter((e) => matches(e, filter.query, filter.status, filter.level));
  if (visible.length === 0) {
    return <p className="text-sm text-slate-600">Tidak ada soal yang cocok dengan filter.</p>;
  }
  return (
    <div className="flex flex-col gap-6">
      {groupByTopic(visible).map((group) => (
        <TopicSection key={group.topic} label={group.label} exercises={group.exercises} />
      ))}
    </div>
  );
}
