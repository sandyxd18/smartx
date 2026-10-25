import { useEffect, useState } from "react";
import { api, type Lesson } from "../api/client";
import { httpErrorMessage, UNREACHABLE } from "../api/errors";
import { Markdown } from "./Markdown";

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ok"; lessons: Lesson[] };

/** Short lessons of one learning step, read next to the work. */
export function LessonsPanel({ step }: { step: number }) {
  const [load, setLoad] = useState<LoadState>({ kind: "loading" });
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.GET("/api/lessons", { params: { query: { step } } }).then(
      ({ data, response }) => {
        if (cancelled) return;
        setLoad(
          data
            ? { kind: "ok", lessons: data }
            : { kind: "error", message: httpErrorMessage(response.status) },
        );
      },
      () => {
        if (!cancelled) setLoad({ kind: "error", message: UNREACHABLE });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [step]);

  let content;
  if (load.kind === "loading")
    content = <p className="text-slate-500">Memuat materi…</p>;
  else if (load.kind === "error")
    content = <p className="text-red-700">{load.message}</p>;
  else {
    const lesson = load.lessons.find((x) => x.id === openId);
    content = lesson ? (
      <div className="flex flex-col gap-2">
        <div>
          <button
            type="button"
            onClick={() => setOpenId(null)}
            className="text-xs text-slate-600 hover:underline"
          >
            ← Daftar materi
          </button>
        </div>
        <Markdown>{lesson.body}</Markdown>
      </div>
    ) : (
      <ul className="flex flex-col gap-1">
        {load.lessons.map((x) => (
          <li key={x.id}>
            <button
              type="button"
              onClick={() => setOpenId(x.id)}
              className="w-full rounded px-2 py-1 text-left hover:bg-slate-100"
            >
              {x.title}
            </button>
          </li>
        ))}
        {load.lessons.length === 0 && (
          <li className="text-slate-500">Belum ada materi.</li>
        )}
      </ul>
    );
  }

  return (
    <aside
      aria-label="Materi"
      className="overflow-auto rounded-lg border border-slate-200 bg-white p-3 text-sm lg:w-96 lg:shrink-0"
    >
      {content}
    </aside>
  );
}
