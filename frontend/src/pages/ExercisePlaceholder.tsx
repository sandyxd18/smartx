import { Link, useParams } from "react-router";

// Replaced by the exercise page (editor, tests, waveform) in Fase 1 task 5.
export function ExercisePlaceholder() {
  const { exerciseId } = useParams();
  return (
    <section>
      <Link to="/latihan" className="text-sm text-slate-600 hover:underline">
        ← Daftar soal
      </Link>
      <h1 className="mt-2 text-2xl font-semibold">{exerciseId}</h1>
      <p className="mt-2 text-slate-600">Halaman soal (editor dan hasil) sedang dibangun.</p>
    </section>
  );
}
