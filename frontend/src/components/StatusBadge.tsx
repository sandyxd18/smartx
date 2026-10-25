import type { RunStatus } from "../api/client";

const LABELS: Record<RunStatus, string> = {
  queued: "Mengantri",
  running: "Berjalan",
  succeeded: "Berhasil",
  failed: "Gagal",
  cancelled: "Dibatalkan",
  timeout: "Melebihi batas waktu",
};

const COLORS: Record<RunStatus, string> = {
  queued: "bg-slate-100 text-slate-700",
  running: "bg-blue-100 text-blue-800",
  succeeded: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  cancelled: "bg-amber-100 text-amber-800",
  timeout: "bg-orange-100 text-orange-800",
};

export function StatusBadge({ status }: { status: RunStatus }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${COLORS[status]}`}>
      {LABELS[status]}
    </span>
  );
}
