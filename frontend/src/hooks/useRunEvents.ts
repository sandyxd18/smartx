import { useEffect, useState } from "react";
import { TERMINAL_STATUSES, type RunStatus } from "../api/client";

export interface RunEvents {
  lines: string[];
  status: RunStatus | null;
}

interface State extends RunEvents {
  runId: string | null;
}

const EMPTY: RunEvents = { lines: [], status: null };

/**
 * Follow a run over SSE (GET /api/runs/{id}/events).
 *
 * The server replays the whole log on every connection, so when EventSource reconnects
 * after a dropped connection the collected lines are reset instead of duplicated.
 */
export function useRunEvents(runId: string | null): RunEvents {
  const [state, setState] = useState<State>({ runId: null, ...EMPTY });

  useEffect(() => {
    if (runId === null) return;
    // State belongs to one run; switching runs starts from EMPTY.
    const update = (fn: (prev: RunEvents) => RunEvents) =>
      setState((prev) => ({ runId, ...fn(prev.runId === runId ? prev : EMPTY) }));

    const source = new EventSource(`/api/runs/${runId}/events`);
    source.addEventListener("open", () => update((prev) => ({ ...prev, lines: [] })));
    source.addEventListener("log", (event) => {
      const { line } = JSON.parse((event as MessageEvent<string>).data) as { line: string };
      update((prev) => ({ ...prev, lines: [...prev.lines, line] }));
    });
    source.addEventListener("status", (event) => {
      const { status } = JSON.parse((event as MessageEvent<string>).data) as {
        status: RunStatus;
      };
      update((prev) => ({ ...prev, status }));
      // The server ends the stream here; closing stops EventSource from reconnecting.
      if (TERMINAL_STATUSES.has(status)) source.close();
    });
    return () => source.close();
  }, [runId]);

  return state.runId === runId ? { lines: state.lines, status: state.status } : EMPTY;
}
