import type { ExerciseStatus, ExerciseSummary } from "../api/client";

/** Curriculum order of the topic groups (first topic of each exercise, see CONTENT-FORMAT). */
const TOPIC_ORDER = ["combinational", "sequential", "fsm", "pitfalls"];

const TOPIC_LABELS: Record<string, string> = {
  combinational: "Kombinasional",
  sequential: "Sekuensial",
  fsm: "FSM",
  pitfalls: "Jebakan umum",
};

export const LEVEL_LABELS: Record<number, string> = { 1: "Dasar", 2: "Menengah", 3: "Lanjut" };

export const STATUS_LABELS: Record<ExerciseStatus, string> = {
  not_started: "Belum",
  attempted: "Gagal",
  solved: "Lulus",
};

export function topicLabel(topic: string): string {
  return TOPIC_LABELS[topic] ?? topic;
}

export interface TopicGroup {
  topic: string;
  label: string;
  exercises: ExerciseSummary[];
}

/** Group by first topic. Known topics come in curriculum order, others alphabetically. */
export function groupByTopic(exercises: ExerciseSummary[]): TopicGroup[] {
  const groups = new Map<string, ExerciseSummary[]>();
  for (const exercise of exercises) {
    const topic = exercise.topics[0] ?? "lainnya";
    groups.set(topic, [...(groups.get(topic) ?? []), exercise]);
  }
  const rank = (topic: string) => {
    const i = TOPIC_ORDER.indexOf(topic);
    return i === -1 ? TOPIC_ORDER.length : i;
  };
  return [...groups.entries()]
    .sort(([a], [b]) => rank(a) - rank(b) || a.localeCompare(b))
    .map(([topic, list]) => ({ topic, label: topicLabel(topic), exercises: list }));
}
