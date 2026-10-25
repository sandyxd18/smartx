export function ComingSoon({ title, phase }: { title: string; phase: number }) {
  return (
    <section>
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="mt-2 text-slate-600">Halaman ini dibangun di Fase {phase}.</p>
    </section>
  );
}

export function NotFound() {
  return (
    <section>
      <h1 className="text-2xl font-semibold">Halaman tidak ditemukan</h1>
    </section>
  );
}
