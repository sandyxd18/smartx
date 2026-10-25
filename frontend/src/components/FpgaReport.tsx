import type { ReactNode } from "react";
import type { CriticalPath, FpgaResult, SynthWarning } from "../api/client";
import { liveStages, resultStages, type StageView } from "../fpga/stages";
import type { ProjectRunState } from "../hooks/useProjectRun";

const MHZ = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 2 });
const NS = new Intl.NumberFormat("id-ID", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const SECONDS = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 1 });
const PERCENT = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 1 });

const STAGE_ICONS: Record<StageView["status"], string> = {
  pending: "○",
  running: "…",
  ok: "✓",
  failed: "✗",
  skipped: "–",
};
const STAGE_TONES: Record<StageView["status"], string> = {
  pending: "text-slate-400",
  running: "text-slate-700",
  ok: "text-green-700",
  failed: "text-red-700",
  skipped: "text-slate-400",
};
const STAGE_LABELS: Record<StageView["status"], string> = {
  pending: "belum",
  running: "berjalan",
  ok: "berhasil",
  failed: "gagal",
  skipped: "dilewati",
};
const WARNING_TITLES: Record<SynthWarning["kind"], string> = {
  latch: "Latch",
  multi_driven: "Banyak driver",
  undriven: "Tanpa driver",
  implicit: "Wire implisit",
  unused_input: "Input tidak dipakai",
  memory_ff: "Memori jadi flip-flop",
  other: "Warning",
};

/** One line for the run panel header while the FPGA tab is open. */
export function FpgaSummary({ fpga }: { fpga: ProjectRunState }): ReactNode {
  if (fpga.running)
    return fpga.status === "queued" ? "Menunggu giliran…" : "Build berjalan…";
  if (fpga.error) return <span className="text-red-700">{fpga.error}</span>;
  const run = fpga.run;
  if (!run)
    return "Klik Build untuk sintesis, place & route, dan membuat bitstream.";
  const result = run.fpga;
  if (run.status !== "succeeded" || !result)
    return <span className="text-red-700">{run.error ?? "Build gagal."}</span>;
  if (result.status === "failed") {
    const stage = result.stages.find((s) => s.status === "failed");
    return (
      <span className="font-medium text-red-700">
        Gagal di {stage?.title ?? "build"}
      </span>
    );
  }
  return (
    <>
      <span className="font-medium text-green-700">Bitstream jadi</span>
      {result.timing_met === false && (
        <span className="font-medium text-red-700">
          {" "}
          · timing tidak tercapai
        </span>
      )}
      {result.timing_met === true && (
        <span className="text-slate-600"> · timing tercapai</span>
      )}
      <span className="text-slate-500"> · {result.board}</span>
    </>
  );
}

export interface FpgaReportProps {
  fpga: ProjectRunState;
  /** Open a project file at a line. */
  onOpenSource: (file: string, line: number) => void;
}

/** The FPGA tab: build stages, then what synthesis and place & route found. */
export function FpgaReport({ fpga, onOpenSource }: FpgaReportProps) {
  if (fpga.running) {
    return (
      <div className="flex flex-col gap-2">
        <StageList stages={liveStages(fpga.lines)} />
        <pre className="font-mono text-xs whitespace-pre-wrap text-slate-600">
          {fpga.lines.slice(-30).join("\n")}
        </pre>
      </div>
    );
  }
  const run = fpga.run;
  const result = run?.fpga;
  if (!run || !result) return null;

  const failed = result.stages.find((s) => s.status === "failed");
  const source = (
    file: string | null | undefined,
    line: number | null | undefined,
  ) =>
    file && line ? (
      <button
        type="button"
        onClick={() => onOpenSource(file, line)}
        className="font-mono text-slate-700 underline decoration-dotted hover:text-slate-900"
      >
        {file}:{line}
      </button>
    ) : null;

  return (
    <div className="flex flex-col gap-3 text-xs">
      <div className="flex flex-wrap items-center gap-3">
        <StageList stages={resultStages(result)} />
        {result.bitstream_url && (
          <a
            href={result.bitstream_url}
            download={`${result.top}-${result.board}${extension(result.bitstream_url)}`}
            className="ml-auto rounded-md bg-slate-900 px-3 py-1 font-medium text-white"
          >
            Unduh bitstream
          </a>
        )}
      </div>
      {result.bitstream_url && (
        <p className="text-slate-600">
          Ke board (di komputer tempat board tercolok):{" "}
          <code className="rounded bg-slate-100 px-1 select-all">
            python tools/flash/smartx-flash --run {run.id}
          </code>{" "}
          · tambah <code>--flash</code> agar tetap ada setelah board dicabut.
        </p>
      )}

      {failed && result.error && (
        <p className="text-red-700">
          <span className="font-medium">{failed.title} gagal:</span>{" "}
          <span className="font-mono">{result.error}</span>
          {result.diagnostics.length > 0 && " Lihat tab Problems."}
        </p>
      )}
      {result.timing_met === false && (
        <p className="rounded border border-red-200 bg-red-50 px-2 py-1 text-red-800">
          Timing tidak tercapai: desain lebih lambat dari target clock.
          Bitstream tetap dibuat, tetapi di board hasilnya bisa salah. Lihat
          jalur kritis di bawah.
        </p>
      )}

      {result.warnings.length > 0 && (
        <section aria-label="Peringatan sintesis">
          <h3 className="mb-1 font-medium text-amber-800">
            Peringatan sintesis ({result.warnings.length})
          </h3>
          <ul className="flex flex-col gap-1">
            {result.warnings.map((w, i) => (
              <li key={i} className="text-amber-900">
                <span className="font-medium">{WARNING_TITLES[w.kind]}</span>
                {w.file && w.line ? <> · {source(w.file, w.line)}</> : null}
                <div className="text-slate-700">{withCode(w.message)}</div>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="flex flex-wrap gap-6">
        {result.utilization.length > 0 && <Resources result={result} />}
        {result.clocks.length > 0 && <Clocks result={result} />}
      </div>

      {result.critical_paths.map((path, i) => (
        <PathView
          key={i}
          path={path}
          open={result.timing_met === false}
          source={source}
        />
      ))}

      <div className="flex gap-3 text-slate-500">
        {result.stages
          .filter((s) => s.log_url)
          .map((s) => (
            <a key={s.id} href={s.log_url ?? undefined} className="underline">
              Log {s.title}
            </a>
          ))}
        {result.report_url && (
          <a href={result.report_url} className="underline">
            report.json
          </a>
        )}
      </div>
    </div>
  );
}

// Messages mark code like Markdown: `led`, and ``x`` for code that holds a backtick.
const CODE = /``\s?(.+?)\s?``|`([^`]+)`/g;

function withCode(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  let last = 0;
  for (const match of text.matchAll(CODE)) {
    parts.push(text.slice(last, match.index));
    parts.push(
      <code key={match.index} className="rounded bg-slate-100 px-0.5">
        {match[1] ?? match[2]}
      </code>,
    );
    last = match.index + match[0].length;
  }
  parts.push(text.slice(last));
  return parts;
}

function extension(url: string): string {
  const name = url.slice(url.lastIndexOf("/") + 1);
  const dot = name.lastIndexOf(".");
  return dot > 0 ? name.slice(dot) : "";
}

function StageList({ stages }: { stages: StageView[] }) {
  return (
    <ol
      aria-label="Tahap build"
      className="flex flex-wrap items-center gap-2 text-xs"
    >
      {stages.map((s, i) => (
        <li key={s.id} className="flex items-center gap-2">
          {i > 0 && (
            <span className="text-slate-300" aria-hidden>
              →
            </span>
          )}
          <span
            className={STAGE_TONES[s.status]}
            aria-label={`${s.title}: ${STAGE_LABELS[s.status]}`}
          >
            <span aria-hidden>{STAGE_ICONS[s.status]}</span> {s.title}
            {s.seconds !== null && (
              <span className="text-slate-500">
                {" "}
                {SECONDS.format(s.seconds)} dtk
              </span>
            )}
          </span>
        </li>
      ))}
    </ol>
  );
}

function Resources({ result }: { result: FpgaResult }) {
  return (
    <table aria-label="Resource" className="text-left">
      <thead className="text-slate-500">
        <tr>
          <th className="pr-4 font-normal">Resource</th>
          <th className="pr-4 text-right font-normal">Terpakai</th>
          <th className="pr-4 text-right font-normal">Tersedia</th>
          <th className="font-normal">%</th>
        </tr>
      </thead>
      <tbody>
        {result.utilization.map((r) => (
          <tr key={r.label} title={r.types.join(" + ")}>
            <td className="pr-4 font-medium">{r.label}</td>
            <td className="pr-4 text-right font-mono">{r.used}</td>
            <td className="pr-4 text-right font-mono">{r.available}</td>
            <td className="flex items-center gap-2">
              <span className="h-1.5 w-20 rounded bg-slate-100">
                <span
                  className={`block h-1.5 rounded ${r.percent > 90 ? "bg-red-500" : "bg-slate-500"}`}
                  style={{ width: `${Math.min(r.percent, 100)}%` }}
                />
              </span>
              <span className="font-mono">{PERCENT.format(r.percent)}%</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Clocks({ result }: { result: FpgaResult }) {
  return (
    <table aria-label="Timing" className="text-left">
      <thead className="text-slate-500">
        <tr>
          <th className="pr-4 font-normal">Clock</th>
          <th className="pr-4 text-right font-normal">Fmax</th>
          <th className="pr-4 text-right font-normal">Target</th>
          <th className="font-normal">Status</th>
        </tr>
      </thead>
      <tbody>
        {result.clocks.map((c) => (
          <tr key={c.net} className={c.met ? "" : "text-red-700"} title={c.net}>
            <td className="pr-4 font-mono font-medium">{c.name}</td>
            <td className="pr-4 text-right font-mono">
              {MHZ.format(c.achieved_mhz)} MHz
            </td>
            <td className="pr-4 text-right font-mono">
              {MHZ.format(c.target_mhz)} MHz
            </td>
            <td
              className={`font-medium ${c.met ? "text-green-700" : "text-red-700"}`}
            >
              {c.met ? "Tercapai" : "Gagal"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function PathView(props: {
  path: CriticalPath;
  open: boolean;
  source: (
    file: string | null | undefined,
    line: number | null | undefined,
  ) => ReactNode;
}) {
  const { path } = props;
  return (
    <details
      open={props.open}
      className="rounded border border-slate-200 px-2 py-1"
    >
      <summary className="cursor-pointer">
        <span className="font-medium">Jalur kritis</span> {path.from_clock} →{" "}
        {path.to_clock}: {NS.format(path.delay_ns)} ns (
        {NS.format(path.logic_ns)} ns logika, {NS.format(path.routing_ns)} ns
        routing)
      </summary>
      <table aria-label="Jalur kritis" className="mt-1 w-full text-left">
        <thead className="text-slate-500">
          <tr>
            <th className="pr-3 font-normal">Jenis</th>
            <th className="pr-3 text-right font-normal">Delay</th>
            <th className="pr-3 text-right font-normal">Total</th>
            <th className="pr-3 font-normal">Net / cell</th>
            <th className="font-normal">Sumber</th>
          </tr>
        </thead>
        <tbody>
          {path.steps.map((s, i) => (
            <tr key={i}>
              <td className="pr-3">{s.type}</td>
              <td className="pr-3 text-right font-mono">
                {NS.format(s.delay_ns)}
              </td>
              <td className="pr-3 text-right font-mono">
                {NS.format(s.total_ns)}
              </td>
              <td className="max-w-80 truncate pr-3 font-mono" title={s.name}>
                {s.name}
              </td>
              <td>{props.source(s.file, s.line)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}
