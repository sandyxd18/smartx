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
export type ExerciseRun = components["schemas"]["ExerciseRunRead"];
export type GradeResult = components["schemas"]["GradeResult"];

export const TERMINAL_STATUSES: ReadonlySet<RunStatus> = new Set([
  "succeeded",
  "failed",
  "cancelled",
  "timeout",
]);

export type ProjectSummary = components["schemas"]["ProjectSummary"];
export type ProjectDetail = components["schemas"]["ProjectDetail"];
export type ProjectEntry = components["schemas"]["EntryRead"];
export type ProjectTemplate = components["schemas"]["ProjectTemplateRead"];
export type ProjectFile = components["schemas"]["FileRead"];
export type ProjectConfig = components["schemas"]["ProjectConfig"];
export type ConfigRead = components["schemas"]["ConfigRead"];
export type ConfigProblem = components["schemas"]["ConfigProblem"];
export type ProjectRun = components["schemas"]["ProjectRunRead"];
export type LintResult = components["schemas"]["LintResult"];
export type LintDiagnostic = components["schemas"]["LintDiagnostic"];
