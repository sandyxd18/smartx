import type { SaveStatus } from "../hooks/useAutosave";

export function SaveIndicator({ status }: { status: SaveStatus }) {
  switch (status) {
    case "pending":
    case "saving":
      return <span className="text-xs text-slate-500">Menyimpan…</span>;
    case "saved":
      return <span className="text-xs text-slate-500">Tersimpan</span>;
    case "error":
      return (
        <span className="text-xs text-red-700">
          Gagal menyimpan. Dicoba lagi saat Anda mengetik.
        </span>
      );
    default:
      return null;
  }
}
