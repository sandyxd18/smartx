import { useEffect, useState } from "react";
import { api, TERMINAL_STATUSES, type Health } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";
import { useRunEvents } from "../hooks/useRunEvents";

type HealthState =
  | { kind: "loading" }
  | { kind: "ok"; health: Health }
  | { kind: "error"; message: string };

/** Explain a non-2xx answer. 502–504 come from the dev proxy when the backend is down. */
function httpErrorMessage(status: number): string {
  return status >= 502 && status <= 504
    ? `Backend tidak bisa dihubungi (HTTP ${status}).`
    : `Backend menjawab HTTP ${status}.`;
}

function HealthCard() {
  const [state, setState] = useState<HealthState>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    api.GET("/api/health").then(
      ({ data, response }) => {
        if (cancelled) return;
        setState(
          data
            ? { kind: "ok", health: data }
            : { kind: "error", message: httpErrorMessage(response.status) },
        );
      },
      () => {
        if (!cancelled) setState({ kind: "error", message: "Backend tidak bisa dihubungi." });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <h2 className="font-medium">Status sistem</h2>
      {state.kind === "loading" && <p className="mt-3 text-sm text-slate-500">Memeriksa…</p>}
      {state.kind === "error" && (
        <div className="mt-3 flex items-center gap-4 text-sm">
          <p className="text-red-700">{state.message}</p>
          <button
            type="button"
            onClick={() => setAttempt((n) => n + 1)}
            className="rounded-md border border-slate-300 px-3 py-1"
          >
            Periksa lagi
          </button>
        </div>
      )}
      {state.kind === "ok" && (
        <dl className="mt-3 grid grid-cols-[8rem_1fr] gap-y-2 text-sm">
          <dt className="text-slate-500">Backend</dt>
          <dd>OK (versi {state.health.version})</dd>
          <dt className="text-slate-500">Docker</dt>
          <dd>
            {state.health.docker.available ? (
              <span className="text-green-700">
                Terdeteksi (versi {state.health.docker.server_version})
              </span>
            ) : (
              <span className="text-red-700">
                Tidak terdeteksi: {state.health.docker.error}
              </span>
            )}
          </dd>
        </dl>
      )}
    </section>
  );
}

function EchoJobCard() {
  const [runId, setRunId] = useState<string | null>(null);
  const [hold, setHold] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { lines, status } = useRunEvents(runId);
  const active = runId !== null && (status === null || !TERMINAL_STATUSES.has(status));

  async function start() {
    setBusy(true);
    setError(null);
    try {
      const { data, response } = await api.POST("/api/runs", {
        body: { kind: "echo", params: hold ? { sleep_s: 60 } : {} },
      });
      if (data) setRunId(data.id);
      else setError(`Gagal membuat run. ${httpErrorMessage(response.status)}`);
    } catch {
      setError("Backend tidak bisa dihubungi.");
    } finally {
      setBusy(false);
    }
  }

  async function cancel() {
    if (runId === null) return;
    try {
      await api.POST("/api/runs/{run_id}/cancel", { params: { path: { run_id: runId } } });
    } catch {
      setError("Gagal membatalkan run.");
    }
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <h2 className="font-medium">Uji pipa job</h2>
      <p className="mt-1 text-sm text-slate-600">
        Menjalankan <code>yosys -V</code> di container toolchain dan menampilkan log secara live.
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-4">
        <button
          type="button"
          onClick={() => void start()}
          disabled={busy || active}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Jalankan echo job
        </button>
        {active && (
          <button
            type="button"
            onClick={() => void cancel()}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm"
          >
            Batalkan
          </button>
        )}
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={hold} onChange={(e) => setHold(e.target.checked)} />
          Tahan 60 detik (untuk menguji Batalkan)
        </label>
      </div>
      {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
      {runId && (
        <div className="mt-4">
          <div className="flex items-center gap-3 text-sm">
            <span className="text-slate-500">
              Run <code>{runId.slice(0, 8)}</code>
            </span>
            {status && <StatusBadge status={status} />}
          </div>
          <pre
            aria-label="Log run"
            className="mt-2 max-h-80 overflow-auto rounded-md bg-slate-900 p-3 text-xs text-slate-100"
          >
            {lines.join("\n") || " "}
          </pre>
        </div>
      )}
    </section>
  );
}

export function Dashboard() {
  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <HealthCard />
      <EchoJobCard />
    </div>
  );
}
