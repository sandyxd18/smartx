"""Build an FPGA bitstream for a project: synthesize, place & route, pack.

Like lint and sim, the API copies the project into <run>/project/ and passes the
resolved smartx.yaml (with its `fpga:` section) as params. prepare() turns the board
profile into one command per stage and tools/fpga/build.py runs them in order,
stopping at the first stage that fails, so the UI can show each stage on its own.
"""

import json
import re
from pathlib import Path, PurePosixPath
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.content.boards import Board, load_boards, nextpnr_command, pack_command
from app.jobs.artifacts import file_url
from app.jobs.context import JobContext, JobInputError
from app.jobs.diagnostics import ProjectDiagnostic, parse_compile_log
from app.jobs.kinds.lint import PROJECT_DIR, ProjectPath
from app.jobs.runner import ContainerSpec, JobClass
from app.projects.config import Name, Scalar
from app.reports.nextpnr import (
    ClockTiming,
    CriticalPath,
    ResourceUse,
    clocks,
    critical_paths,
    input_ports,
    utilization,
)
from app.reports.yosys import SynthWarning, parse_yosys_log, unused_input_warnings

JOB_CLASS = JobClass.light
# build.py: 0 = bitstream written, 1 = a stage failed (still a result).
OK_EXIT_CODES = frozenset({0, 1})

SPEC_FILE = "fpga.json"
WORK_DIR = "build"  # every stage runs here; outputs land here
RESULT_FILE = "result.json"
SYNTH_SCRIPT = "synth.ys"
NETLIST_FILE = "netlist.json"
REPORT_FILE = "report.json"
STAT_FILE = "stat.txt"
STAT_JSON_FILE = "stat.json"
STAGE_LOGS = {"synth": "yosys.log", "pnr": "nextpnr.log"}  # pack only writes to the run log

PROJECT_ROOT = f"/work/{PROJECT_DIR}"
# A value is written into a Yosys script: one token, no quotes or comments.
_SCRIPT_TOKEN = re.compile(r'^[^\s;"#]+$')
_ERROR_LINE = re.compile(r"^(?:.*: )?ERROR: (?P<msg>.+)$")


class Params(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top: Name
    sources: Annotated[list[ProjectPath], Field(min_length=1)]
    defines: dict[Name, Scalar] = {}
    parameters: dict[Name, Scalar] = {}
    board: str
    constraints: ProjectPath
    freq_mhz: float = Field(gt=0, le=1000)


class FpgaStage(BaseModel):
    id: Literal["synth", "pnr", "pack"]
    title: str
    status: Literal["ok", "failed", "skipped"]
    seconds: float | None = None
    log_url: str | None = None  # the stage's full log, when it writes one


class FpgaResult(BaseModel):
    """Run.result of an fpga run."""

    status: Literal["ok", "failed"]
    board: str
    top: str
    freq_mhz: float
    stages: list[FpgaStage]
    error: str | None = None  # first ERROR line of the stage that failed
    # Yosys messages about project files (only when synthesis failed).
    diagnostics: list[ProjectDiagnostic] = []
    versions: dict[str, str] = {}
    bitstream_url: str | None = None
    report_url: str | None = None  # nextpnr report.json
    stat_url: str | None = None  # Yosys stat
    # Report (empty until the stage that writes it has run).
    warnings: list[SynthWarning] = []  # from synthesis
    utilization: list[ResourceUse] = []  # from place & route
    clocks: list[ClockTiming] = []
    timing_met: bool | None = None  # None: no clocked logic, or no report
    critical_paths: list[CriticalPath] = []


def _board(ctx: JobContext, board_id: str) -> Board:
    for profile in load_boards(ctx.settings.content_dir / "boards"):
        if profile.board.id == board_id:
            return profile.board
    raise JobInputError(f"Board '{board_id}' tidak dikenal.")


def _token(kind: str, name: str, value: object) -> str:
    text = str(value)
    if not _SCRIPT_TOKEN.match(text):
        raise JobInputError(
            f"Nilai {kind} '{name}' tidak bisa dipakai untuk sintesis "
            "(tanpa spasi, tanda kutip, ';', atau '#')."
        )
    return text


def synth_script(p: Params, board: Board) -> str:
    """Yosys script: read the sources, set parameters, synthesize, write the stats."""
    sources = [f"{PROJECT_ROOT}/{s}" for s in p.sources]
    folders = dict.fromkeys(str(PurePosixPath(s).parent) for s in sources)
    flags = [f"-I{folder}" for folder in folders]
    flags += [f"-D{name}={_token('define', name, v)}" for name, v in p.defines.items()]
    lines = []
    for sv, files in (
        (False, [s for s in sources if not s.endswith(".sv")]),
        (True, [s for s in sources if s.endswith(".sv")]),
    ):
        if files:
            lines.append(" ".join(["read_verilog", *(["-sv"] if sv else []), *flags, *files]))
    if p.parameters:
        sets = [f"-set {name} {_token('parameter', name, v)}" for name, v in p.parameters.items()]
        lines.append(f"chparam {' '.join(sets)} {p.top}")
    lines += [
        f"{board.synth} -top {p.top} -json {NETLIST_FILE}",
        f"tee -q -o {STAT_FILE} stat",
        f"tee -q -o {STAT_JSON_FILE} stat -json",
    ]
    return "\n".join(lines) + "\n"


def prepare(run_dir: Path, params: dict[str, Any], ctx: JobContext) -> ContainerSpec:
    p = Params.model_validate(params)
    board = _board(ctx, p.board)
    for path in [*p.sources, p.constraints]:
        if not (run_dir / PROJECT_DIR / path).is_file():
            raise JobInputError(f"File '{path}' tidak ada di salinan proyek.")

    work = run_dir / WORK_DIR
    work.mkdir(parents=True, exist_ok=True)
    (work / SYNTH_SCRIPT).write_text(synth_script(p, board), encoding="utf-8", newline="\n")
    pnr = nextpnr_command(
        board,
        netlist=NETLIST_FILE,
        constraints=f"{PROJECT_ROOT}/{p.constraints}",
        freq_mhz=p.freq_mhz,
        report=REPORT_FILE,
        log=STAGE_LOGS["pnr"],
    )
    spec = {
        "board": board.id,
        "top": p.top,
        "freq_mhz": p.freq_mhz,
        "sources": p.sources,
        "resources": board.resources,
        "bitstream_file": board.bitstream_file,
        "stages": [
            {
                "id": "synth",
                "title": "Synthesize",
                "command": ["yosys", "-q", "-l", STAGE_LOGS["synth"], "-s", SYNTH_SCRIPT],
            },
            # A design that misses timing still gets a bitstream; the report says so.
            {"id": "pnr", "title": "Place & Route", "command": [*pnr, "-q", "--timing-allow-fail"]},
            {"id": "pack", "title": "Pack", "command": pack_command(board)},
        ],
        "versions": {"yosys": ["yosys", "-V"], "nextpnr": [board.nextpnr.binary, "--version"]},
    }
    (run_dir / SPEC_FILE).write_text(json.dumps(spec, indent=2), encoding="utf-8", newline="\n")
    return ContainerSpec(
        command=[
            "python",
            "/tools/fpga/build.py",
            "--spec",
            f"/work/{SPEC_FILE}",
            "--workdir",
            f"/work/{WORK_DIR}",
            "--out",
            f"/work/{RESULT_FILE}",
        ],
        job_class=JOB_CLASS,
        # gowin_pack (Apicula) warns about optional speedups on every start.
        env={"PYTHONWARNINGS": "ignore"},
        mount_tools=True,
    )


def _work_file(run_dir: Path, name: str) -> str | None:
    rel = f"{WORK_DIR}/{name}"
    return file_url(run_dir, rel) if (run_dir / rel).is_file() else None


def _first_error(run_dir: Path, stage: str) -> str | None:
    # The pack stage writes no log of its own; its output is only in the run log.
    log = run_dir / WORK_DIR / STAGE_LOGS[stage] if stage in STAGE_LOGS else run_dir / "run.log"
    text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    for line in text.splitlines():
        if match := _ERROR_LINE.match(line.strip()):
            return match["msg"].strip()
    return None


def _read_json(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _warnings(
    run_dir: Path, spec: dict[str, Any], netlist: dict[str, Any] | None
) -> list[SynthWarning]:
    log = run_dir / WORK_DIR / STAGE_LOGS["synth"]
    if not log.is_file():
        return []
    sources = {}
    for rel in spec["sources"]:
        path = run_dir / PROJECT_DIR / rel
        if path.is_file():
            sources[rel] = path.read_text(encoding="utf-8", errors="replace")
    text = log.read_text(encoding="utf-8", errors="replace")
    found = parse_yosys_log(text, sources, PROJECT_ROOT)
    if netlist is not None:
        found += unused_input_warnings(netlist, spec["top"], sources)
    return found


def collect(run_dir: Path) -> dict[str, Any]:
    spec = json.loads((run_dir / SPEC_FILE).read_text(encoding="utf-8"))
    data = json.loads((run_dir / RESULT_FILE).read_text(encoding="utf-8"))
    stages = [
        FpgaStage(
            id=s["id"],
            title=s["title"],
            status=s["status"],
            seconds=s.get("seconds"),
            log_url=_work_file(run_dir, STAGE_LOGS[s["id"]]) if s["id"] in STAGE_LOGS else None,
        )
        for s in data["stages"]
    ]
    failed = next((s for s in stages if s.status == "failed"), None)
    diagnostics = []
    if failed is not None and failed.id == "synth":
        log = run_dir / WORK_DIR / STAGE_LOGS["synth"]
        if log.is_file():
            diagnostics = parse_compile_log(
                log.read_text(encoding="utf-8", errors="replace"), PROJECT_ROOT
            )
    report = _read_json(run_dir / WORK_DIR / REPORT_FILE)
    netlist = _read_json(run_dir / WORK_DIR / NETLIST_FILE)
    ports = input_ports(netlist, spec["top"]) if netlist else {}
    timing = clocks(report, ports) if report else []
    result = FpgaResult(
        status="failed" if failed else "ok",
        board=spec["board"],
        top=spec["top"],
        freq_mhz=spec["freq_mhz"],
        stages=stages,
        error=_first_error(run_dir, failed.id) if failed else None,
        diagnostics=[ProjectDiagnostic.model_validate(d) for d in diagnostics],
        versions={k: v for k, v in (data.get("versions") or {}).items() if v},
        bitstream_url=_work_file(run_dir, spec["bitstream_file"]) if not failed else None,
        report_url=_work_file(run_dir, REPORT_FILE),
        stat_url=_work_file(run_dir, STAT_FILE),
        warnings=_warnings(run_dir, spec, netlist),
        utilization=utilization(report, spec["resources"]) if report else [],
        clocks=timing,
        timing_met=all(c.met for c in timing) if timing else None,
        critical_paths=critical_paths(report, PROJECT_ROOT, ports) if report else [],
    )
    return result.model_dump()
