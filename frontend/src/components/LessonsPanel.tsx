import { useEffect, useMemo, useState } from "react";
import { api, type Lesson } from "../api/client";
import { httpErrorMessage, UNREACHABLE } from "../api/errors";
import { Markdown } from "./Markdown";

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ok"; lessons: Lesson[] };

const STEP_TITLES: Record<number, string> = {
  1: "Langkah 1 · Latihan Verilog",
  2: "Langkah 2 · Simulasi dan verifikasi",
  3: "Langkah 3 · FPGA",
  4: "Langkah 4 · Proyek bertahap",
  5: "Langkah 5 · ASIC",
  6: "Langkah 6 · Tapeout",
};

/** Short lessons of some learning steps, grouped per step, read next to the work. */
export function LessonsPanel({ steps }: { steps: number[] }) {
  const [load, setLoad] = useState<LoadState>({ kind: "loading" });
  const [openId, setOpenId] = useState<string | null>(null);
  // A stable dependency for the effect, whatever array the caller passes.
  const key = steps.join(",");
  const wanted = useMemo(() => key.split(",").map(Number), [key]);

  useEffect(() => {
    let cancelled = false;
    api.GET("/api/lessons").then(
      ({ data, response }) => {
        if (cancelled) return;
        setLoad(
          data
            ? {
                kind: "ok",
                lessons: data.filter((x) => wanted.includes(x.step)),
              }
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
  }, [wanted]);

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
    ) : load.lessons.length === 0 ? (
      <p className="text-slate-500">Belum ada materi.</p>
    ) : (
      <div className="flex flex-col gap-3">
        {wanted.map((step) => {
          const items = load.lessons.filter((x) => x.step === step);
          if (items.length === 0) return null;
          return (
            <section
              key={step}
              aria-label={STEP_TITLES[step] ?? `Langkah ${step}`}
            >
              <h2 className="mb-1 text-xs font-medium text-slate-500">
                {STEP_TITLES[step] ?? `Langkah ${step}`}
              </h2>
              <ul className="flex flex-col gap-1">
                {items.map((x) => (
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
              </ul>
            </section>
          );
        })}
      </div>
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
