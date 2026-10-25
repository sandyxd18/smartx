import { useCallback, useEffect, useState } from "react";
import {
  api,
  TERMINAL_STATUSES,
  type ProjectDiagnostic,
  type ProjectRun,
} from "../api/client";
import { apiErrorMessage, httpErrorMessage, UNREACHABLE } from "../api/errors";
import { useRunEvents } from "./useRunEvents";

export type ProjectRunKind = "lint" | "sim" | "fpga";

/**
 * Start a job on a project and follow it until it is finished.
 * `beforeStart` runs first (store pending edits: the run copies the saved files).
 */
export function useProjectRun(
  projectId: number,
  beforeStart: () => Promise<void>,
) {
  const [run, setRun] = useState<ProjectRun | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const events = useRunEvents(pendingId);

  useEffect(() => {
    if (pendingId === null || events.status === null) return;
    if (!TERMINAL_STATUSES.has(events.status)) return;
    let cancelled = false;
    api
      .GET("/api/projects/{project_id}/runs/{run_id}", {
        params: { path: { project_id: projectId, run_id: pendingId } },
      })
      .then(
        ({ data, response }) => {
          if (cancelled) return;
          if (data) setRun(data);
          else
            setError(
              `Gagal membaca hasil run. ${httpErrorMessage(response.status)}`,
            );
          setPendingId(null);
        },
        () => {
          if (!cancelled) setError(UNREACHABLE);
        },
      );
    return () => {
      cancelled = true;
    };
  }, [events.status, pendingId, projectId]);

  const start = useCallback(
    async (kind: ProjectRunKind) => {
      if (pendingId !== null) return;
      setError(null);
      await beforeStart();
      try {
        const {
          data,
          error: apiError,
          response,
        } = await api.POST("/api/projects/{project_id}/runs", {
          params: { path: { project_id: projectId } },
          body: { kind },
        });
        if (!data) {
          setError(apiErrorMessage(apiError, response.status));
          return;
        }
        setRun(data);
        setPendingId(data.id);
      } catch {
        setError(UNREACHABLE);
      }
    },
    [pendingId, beforeStart, projectId],
  );

  /** Show a finished run from the history (ignored while a run is going). */
  const show = useCallback(
    (past: ProjectRun) => {
      if (pendingId !== null) return;
      setError(null);
      setRun(past);
    },
    [pendingId],
  );

  return {
    run,
    show,
    running: pendingId !== null,
    status:
      pendingId !== null ? (events.status ?? "queued") : (run?.status ?? null),
    /** Log lines streamed while the run is going. */
    lines: events.lines,
    error,
    start,
  };
}

export type ProjectRunState = Omit<
  ReturnType<typeof useProjectRun>,
  "start" | "show"
>;

/**
 * Lint findings, the compile errors of the last simulation, and what the last FPGA
 * build found in the sources (synthesis errors, and warnings that have a line).
 */
export function projectProblems(
  lint: ProjectRunState,
  sim: ProjectRunState,
  fpga?: ProjectRunState,
): ProjectDiagnostic[] {
  const build = fpga?.run?.fpga;
  const synthWarnings: ProjectDiagnostic[] = (build?.warnings ?? []).flatMap(
    (w) =>
      w.file && w.line
        ? [
            {
              file: w.file,
              line: w.line,
              severity: "warning",
              code: "Yosys",
              message: w.message,
            },
          ]
        : [],
  );
  return [
    ...(lint.run?.lint?.diagnostics ?? []),
    ...(sim.run?.sim?.diagnostics ?? []),
    ...(build?.diagnostics ?? []),
    ...synthWarnings,
  ];
}
