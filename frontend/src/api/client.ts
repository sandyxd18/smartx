import createClient from "openapi-fetch";
import type { components, paths } from "./schema";

export const api = createClient<paths>({
  baseUrl: globalThis.location?.origin ?? "",
  // Look fetch up on every call so tests can stub it after this module is loaded.
  fetch: (request) => globalThis.fetch(request),
});

export type Health = components["schemas"]["HealthResponse"];
export type Run = components["schemas"]["RunRead"];
export type RunStatus = components["schemas"]["RunStatus"];
export type ExerciseSummary = components["schemas"]["ExerciseSummary"];
export type ExerciseDetail = components["schemas"]["ExerciseDetail"];
export type ExerciseStatus = components["schemas"]["ExerciseStatus"];

export const TERMINAL_STATUSES: ReadonlySet<RunStatus> = new Set([
  "succeeded",
  "failed",
  "cancelled",
  "timeout",
]);
