import { useEffect, useId, useState } from "react";
import { api, type Board, type ProjectConfig } from "../api/client";
import { apiErrorMessage, httpErrorMessage, UNREACHABLE } from "../api/errors";

type Fpga = NonNullable<ProjectConfig["fpga"]>;

export interface FpgaPanelProps {
  projectId: number;
  /** Paths of the project's files, to tell whether a constraint file exists. */
  files: string[];
  /** Store pending edits before smartx.yaml is rewritten. */
  settle: () => Promise<void>;
  /** smartx.yaml was saved with this text. */
  onConfigSaved: (text: string) => void;
  /** A file was created (the tree must be read again). */
  onFileCreated: () => Promise<void>;
  onOpenFile: (path: string) => void;
}

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ok"; boards: Board[]; config: ProjectConfig | null };

function defaultConstraints(board: Board): string {
  return `constraints/${board.id}.${board.constraints_format}`;
}

/** Board, target clock and constraint file: the `fpga` section of smartx.yaml. */
export function FpgaPanel(props: FpgaPanelProps) {
  const { projectId, files, settle, onConfigSaved, onFileCreated, onOpenFile } =
    props;
  const [load, setLoad] = useState<LoadState>({ kind: "loading" });
  const [freq, setFreq] = useState("");
  const [constraints, setConstraints] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const idPrefix = useId();

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.GET("/api/boards"),
      api.GET("/api/projects/{project_id}/config", {
        params: { path: { project_id: projectId } },
      }),
    ]).then(
      ([boards, config]) => {
        if (cancelled) return;
        if (!boards.data || !config.data) {
          const status = boards.data
            ? config.response.status
            : boards.response.status;
          setLoad({ kind: "error", message: httpErrorMessage(status) });
          return;
        }
        const fpga = config.data.config?.fpga;
        setFreq(fpga?.freq_mhz ? String(fpga.freq_mhz) : "");
        setConstraints(fpga?.constraints ?? "");
        setLoad({
          kind: "ok",
          boards: boards.data,
          config: config.data.config ?? null,
        });
      },
      () => {
        if (!cancelled) setLoad({ kind: "error", message: UNREACHABLE });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  if (load.kind === "loading") return <Shell>Memuat board…</Shell>;
  if (load.kind === "error")
    return (
      <Shell>
        <p className="text-red-700">{load.message}</p>
      </Shell>
    );

  const { boards, config } = load;
  const fpga = config?.fpga ?? null;
  const board = boards.find((b) => b.id === fpga?.board) ?? null;

  /** Save the fpga section; the rest of smartx.yaml is read fresh so edits are not lost. */
  async function save(next: Fpga): Promise<boolean> {
    setError(null);
    await settle();
    try {
      const current = await api.GET("/api/projects/{project_id}/config", {
        params: { path: { project_id: projectId } },
      });
      const base = current.data?.config;
      if (!base) {
        setError(
          "smartx.yaml belum valid. Perbaiki dulu di editor, lalu coba lagi.",
        );
        return false;
      }
      const {
        data,
        error: apiError,
        response,
      } = await api.PUT("/api/projects/{project_id}/config", {
        params: { path: { project_id: projectId } },
        body: { ...base, fpga: next },
      });
      if (!data) {
        setError(apiErrorMessage(apiError, response.status));
        return false;
      }
      setLoad({ kind: "ok", boards, config: data.config ?? null });
      onConfigSaved(data.text);
      return true;
    } catch {
      setError(UNREACHABLE);
      return false;
    }
  }

  /** Pick a board: its constraint template becomes a project file if there is none. */
  async function chooseBoard(id: string) {
    const chosen = boards.find((b) => b.id === id);
    if (!chosen) return;
    setBusy(true);
    try {
      const path =
        fpga?.board === id && fpga.constraints
          ? fpga.constraints
          : defaultConstraints(chosen);
      let created = false;
      if (!files.includes(path)) {
        const { error: apiError, response } = await api.POST(
          "/api/projects/{project_id}/files",
          {
            params: { path: { project_id: projectId } },
            body: { path, content: chosen.constraints_template },
          },
        );
        if (!response.ok && response.status !== 409) {
          setError(apiErrorMessage(apiError, response.status));
          return;
        }
        created = response.ok;
      }
      setConstraints(path);
      setFreq("");
      if (await save({ board: id, constraints: path })) {
        if (created) await onFileCreated();
        onOpenFile(path);
      }
    } catch {
      setError(UNREACHABLE);
    } finally {
      setBusy(false);
    }
  }

  async function saveFreq() {
    if (!fpga) return;
    const text = freq.trim().replace(",", ".");
    const value = text === "" ? null : Number(text);
    if (value !== null && !(value > 0 && value <= 1000)) {
      setError(
        "Target clock harus angka MHz lebih dari 0 dan paling besar 1000.",
      );
      return;
    }
    if (value === (fpga.freq_mhz ?? null)) return;
    await save({ ...fpga, freq_mhz: value });
  }

  async function saveConstraints() {
    if (!fpga) return;
    const path = constraints.trim();
    if (path === "" || path === fpga.constraints) {
      setConstraints(fpga.constraints);
      return;
    }
    await save({ ...fpga, constraints: path });
  }

  async function createFromTemplate() {
    if (!fpga || !board) return;
    setError(null);
    try {
      const { error: apiError, response } = await api.POST(
        "/api/projects/{project_id}/files",
        {
          params: { path: { project_id: projectId } },
          body: { path: fpga.constraints, content: board.constraints_template },
        },
      );
      if (!response.ok) {
        setError(apiErrorMessage(apiError, response.status));
        return;
      }
      await onFileCreated();
      onOpenFile(fpga.constraints);
    } catch {
      setError(UNREACHABLE);
    }
  }

  const missing = fpga !== null && !files.includes(fpga.constraints);

  return (
    <Shell>
      <label className="flex flex-col gap-1">
        <span className="font-medium">Board</span>
        <select
          value={fpga?.board ?? ""}
          disabled={busy || config === null}
          onChange={(e) => void chooseBoard(e.target.value)}
          className="rounded-md border border-slate-300 px-2 py-1"
        >
          <option value="" disabled>
            Pilih board…
          </option>
          {fpga && !board && (
            <option value={fpga.board}>{fpga.board} (tidak dikenal)</option>
          )}
          {boards.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
      </label>
      {config === null && (
        <p className="text-red-700">
          smartx.yaml belum valid. Perbaiki dulu di editor.
        </p>
      )}
      {board && (
        <p className="text-xs text-slate-500">
          {board.device} · clock {board.clock_mhz} MHz di port{" "}
          <code>{board.clock_port}</code> (pin {board.clock_pin})
        </p>
      )}

      {fpga && (
        <>
          <label className="flex flex-col gap-1">
            <span className="font-medium">Target clock (MHz)</span>
            <input
              inputMode="decimal"
              value={freq}
              placeholder={board ? `${board.clock_mhz} (clock board)` : ""}
              onChange={(e) => setFreq(e.target.value)}
              onBlur={() => void saveFreq()}
              onKeyDown={(e) => {
                if (e.key === "Enter") void saveFreq();
              }}
              aria-describedby={`${idPrefix}-freq-hint`}
              className="rounded-md border border-slate-300 px-2 py-1 font-mono"
            />
          </label>
          <p
            id={`${idPrefix}-freq-hint`}
            className="-mt-2 text-xs text-slate-500"
          >
            Kosongkan untuk memakai clock board. Place &amp; route memeriksa
            timing terhadap angka ini.
          </p>

          <label className="flex flex-col gap-1">
            <span className="font-medium">File constraint</span>
            <input
              value={constraints}
              onChange={(e) => setConstraints(e.target.value)}
              onBlur={() => void saveConstraints()}
              onKeyDown={(e) => {
                if (e.key === "Enter") void saveConstraints();
              }}
              className="rounded-md border border-slate-300 px-2 py-1 font-mono"
            />
          </label>
          <div className="flex gap-2">
            {missing ? (
              <button
                type="button"
                onClick={() => void createFromTemplate()}
                className="rounded-md border border-slate-300 px-3 py-1"
              >
                Buat dari template board
              </button>
            ) : (
              <button
                type="button"
                onClick={() => onOpenFile(fpga.constraints)}
                className="rounded-md border border-slate-300 px-3 py-1"
              >
                Buka di editor
              </button>
            )}
          </div>
          {missing && (
            <p className="text-xs text-amber-800">
              File constraint belum ada di proyek.
            </p>
          )}
          <p className="text-xs text-slate-500">
            Nama port di modul top harus sama dengan nama di file constraint
            (misalnya <code>clk</code>, <code>led[0]</code>). Port yang tidak
            dipakai boleh dibiarkan.
          </p>
        </>
      )}
      {error && <p className="text-red-700">{error}</p>}
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <aside
      aria-label="Pengaturan FPGA"
      className="flex flex-col gap-3 overflow-auto rounded-lg border border-slate-200 bg-white p-3 text-sm lg:w-80 lg:shrink-0"
    >
      <h2 className="font-semibold">FPGA</h2>
      {children}
    </aside>
  );
}
