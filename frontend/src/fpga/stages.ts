import type { FpgaResult } from "../api/client";

export type StageStatus = "pending" | "running" | "ok" | "failed" | "skipped";

export interface StageView {
  id: string;
  title: string;
  status: StageStatus;
  seconds: number | null;
  logUrl: string | null;
}

/** The fpga job's stages, in order (titles as tools/fpga/build.py prints them). */
export const STAGES = [
  { id: "synth", title: "Synthesize" },
  { id: "pnr", title: "Place & Route" },
  { id: "pack", title: "Pack" },
] as const;

// build.py starts the run log with "stages: Synthesize | Place & Route", then marks each
// stage: "==> Pack" and "<== Pack: ok (2.73 s)". Boards without a packer have no Pack.
const PLAN = "stages: ";
const END = /^<== (.+): (ok|failed) \(([\d.]+) s\)$/;

/** Stage progress read from the log lines streamed while a build runs. */
export function liveStages(lines: string[]): StageView[] {
  const started = new Set<string>();
  const ended = new Map<string, { status: StageStatus; seconds: number }>();
  let planned: string[] | null = null;
  for (const line of lines) {
    if (line.startsWith(PLAN)) planned = line.slice(PLAN.length).trim().split(" | ");
    if (line.startsWith("==> ")) started.add(line.slice(4).trim());
    const [, title, status, seconds] = END.exec(line.trim()) ?? [];
    if (title && status && seconds) {
      ended.set(title, {
        status: status as StageStatus,
        seconds: Number(seconds),
      });
    }
  }
  const stages = planned
    ? planned.map(
        (title) =>
          STAGES.find((s) => s.title === title) ?? { id: title, title },
      )
    : STAGES;
  return stages.map(({ id, title }) => {
    const done = ended.get(title);
    return {
      id,
      title,
      status: done?.status ?? (started.has(title) ? "running" : "pending"),
      seconds: done?.seconds ?? null,
      logUrl: null,
    };
  });
}

/** Stages of a finished build. */
export function resultStages(result: FpgaResult): StageView[] {
  return result.stages.map((s) => ({
    id: s.id,
    title: s.title,
    status: s.status,
    seconds: s.seconds ?? null,
    logUrl: s.log_url ?? null,
  }));
}
