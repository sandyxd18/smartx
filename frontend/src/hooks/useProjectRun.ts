import { useCallback, useEffect, useState } from "react";
import { api, TERMINAL_STATUSES, type ProjectRun } from "../api/client";
import { apiErrorMessage, httpErrorMessage, UNREACHABLE } from "../api/errors";
import { useRunEvents } from "./useRunEvents";

export type ProjectRunKind = "lint";

/**
 * Start a job on a project and follow it until it is finished.
 * `beforeStart` runs first (store pending edits: the run copies the saved files).
 */
export function useProjectRun(projectId: number, beforeStart: () => Promise<void>) {
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
          else setError(`Gagal membaca hasil run. ${httpErrorMessage(response.status)}`);
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
        const { data, error: apiError, response } = await api.POST(
          "/api/projects/{project_id}/runs",
          { params: { path: { project_id: projectId } }, body: { kind } },
        );
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

  return {
    run,
    running: pendingId !== null,
    status: pendingId !== null ? (events.status ?? "queued") : (run?.status ?? null),
    error,
    start,
  };
}
