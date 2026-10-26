"""End-to-end job tests against the real Docker daemon and toolchain image.

Skipped by default. Run with: SMARTX_DOCKER_TESTS=1 uv run pytest tests/integration
"""

import asyncio
import json
import os
import shlex
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import docker
import pytest
from sqlalchemy import Engine
from sqlmodel import Session

from app.config import REPO_ROOT, Settings
from app.content import ExerciseCatalog
from app.content.boards import (
    BoardProfile,
    load_boards,
    nextpnr_command,
    pack_command,
    synth_commands,
)
from app.db import init_db, make_engine
from app.jobs.context import JobContext
from app.jobs.docker_runner import RUN_LABEL, DockerRunner
from app.jobs.events import EventHub
from app.jobs.kinds import KINDS
from app.jobs.queue import JobQueue
from app.jobs.runner import ContainerSpec, JobClass
from app.models import Run, RunStatus
from app.projects.run_params import run_params
from app.projects.snapshot import write_snapshot
from app.projects.snippets import assemble, load_snippets
from app.projects.templates import load_templates

pytestmark = pytest.mark.skipif(
    os.environ.get("SMARTX_DOCKER_TESTS") != "1", reason="set SMARTX_DOCKER_TESTS=1"
)

SANDBOX_SCRIPT = (
    "echo uid=$(id -u); "
    "echo net=$(ls /sys/class/net | tr '\\n' ' '); "
    "touch /work/written && echo work=rw; "
    "touch /content/x 2>/dev/null && echo content=rw || echo content=ro"
)

BOARD_FIXTURES = Path(__file__).parents[1] / "fixtures" / "boards"
BOARDS = {p.board.id: p for p in load_boards(REPO_ROOT / "content" / "boards")}


def prepare_board_check(run_dir: Path, params: dict[str, Any], ctx: object) -> ContainerSpec:
    """Synthesize, place, route and pack a blinky with nothing but a board profile."""
    profile: BoardProfile = BOARDS[params["board"]]
    board = profile.board
    (run_dir / "blinky.v").write_bytes((BOARD_FIXTURES / board.id / "blinky.v").read_bytes())
    (run_dir / "board.cst").write_text(profile.constraints_template, encoding="utf-8")
    synth = "; ".join(["read_verilog blinky.v", *synth_commands(board, "blinky", "netlist.json")])
    steps = [
        ["yosys", "-q", "-l", "yosys.log", "-p", synth],
        nextpnr_command(
            board,
            netlist="netlist.json",
            constraints="board.cst",
            freq_mhz=board.clock.freq_mhz,
            report="report.json",
            log="nextpnr.log",
        ),
    ]
    if (pack := pack_command(board)) is not None:
        steps.append(pack)
    return ContainerSpec(command=["sh", "-c", " && ".join(shlex.join(s) for s in steps)])


KINDS_UNDER_TEST = {
    **KINDS,
    "board_check": SimpleNamespace(
        JOB_CLASS=JobClass.light,
        OK_EXIT_CODES=frozenset({0}),
        prepare=prepare_board_check,
        collect=lambda run_dir: {},
    ),
    "sandbox": SimpleNamespace(
        JOB_CLASS=JobClass.light,
        OK_EXIT_CODES=frozenset({0}),
        prepare=lambda run_dir, params, ctx: ContainerSpec(
            command=["sh", "-c", SANDBOX_SCRIPT], mount_content=True
        ),
        collect=lambda run_dir: {},
    ),
}


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = make_engine("sqlite://")
    init_db(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def docker_settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        content_dir=REPO_ROOT / "content",
        job_light_timeout_s=20,
    )


def make_queue(settings: Settings, engine: Engine) -> JobQueue:
    return JobQueue(
        runner=DockerRunner(settings),
        settings=settings,
        engine=engine,
        events=EventHub(),
        context=JobContext(
            settings=settings,
            catalog=ExerciseCatalog(settings.content_dir / "exercises", auto_reload=False),
        ),
        kinds=KINDS_UNDER_TEST,
    )


def new_run(engine: Engine, kind: str, params: dict[str, Any] | None = None) -> str:
    with Session(engine) as s:
        run = Run(kind=kind, params=params or {})
        s.add(run)
        s.commit()
        return run.id


def get_run(engine: Engine, run_id: str) -> Run:
    with Session(engine) as s:
        run = s.get(Run, run_id)
        assert run is not None
        return run


def containers_for(run_id: str) -> list[object]:
    client = docker.from_env()
    try:
        return client.containers.list(all=True, filters={"label": f"{RUN_LABEL}={run_id}"})
    finally:
        client.close()


async def test_echo_job_succeeds(docker_settings: Settings, engine: Engine) -> None:
    queue = make_queue(docker_settings, engine)
    run_id = new_run(engine, "echo")

    await queue.submit(run_id)

    run = get_run(engine, run_id)
    assert run.status == RunStatus.succeeded, run.error
    assert run.result is not None and run.result["yosys_version"].startswith("Yosys ")
    assert run.tool_versions is not None and run.tool_versions["image_id"].startswith("sha256:")
    assert containers_for(run_id) == []


async def test_sandbox_restrictions(docker_settings: Settings, engine: Engine) -> None:
    queue = make_queue(docker_settings, engine)
    run_id = new_run(engine, "sandbox")

    await queue.submit(run_id)

    assert get_run(engine, run_id).status == RunStatus.succeeded
    log = (docker_settings.runs_dir / run_id / "run.log").read_text().splitlines()
    assert "uid=0" not in log
    assert "net=lo" in log  # loopback only: --network none
    assert "work=rw" in log
    assert "content=ro" in log


async def test_cancel_long_job_removes_container(docker_settings: Settings, engine: Engine) -> None:
    queue = make_queue(docker_settings, engine)
    run_id = new_run(engine, "echo", {"sleep_s": 60})

    task = queue.submit(run_id)
    async with asyncio.timeout(30):
        while get_run(engine, run_id).status != RunStatus.running or not containers_for(run_id):
            await asyncio.sleep(0.2)
        await queue.cancel(run_id)
        await task

    assert get_run(engine, run_id).status == RunStatus.cancelled
    assert containers_for(run_id) == []


async def test_timeout_kills_long_job(docker_settings: Settings, engine: Engine) -> None:
    settings = docker_settings.model_copy(update={"job_light_timeout_s": 3})
    queue = make_queue(settings, engine)
    run_id = new_run(engine, "echo", {"sleep_s": 60})

    async with asyncio.timeout(30):
        await queue.submit(run_id)

    assert get_run(engine, run_id).status == RunStatus.timeout
    assert containers_for(run_id) == []


COUNTER = REPO_ROOT / "content" / "exercises" / "counter-4bit"

PEEK_AT_SOLUTION = """module counter4(input clk, input rst, input en, output reg [3:0] q);
  integer fd;
  initial begin
    fd = $fopen("/content/exercises/counter-4bit/solution.v", "r");
    $display("PEEK fd=%0d", fd);
  end
endmodule
"""


async def grade_code(settings: Settings, engine: Engine, code: str) -> Run:
    queue = make_queue(settings, engine)
    run_id = new_run(engine, "grade", {"exercise_id": "counter-4bit", "code": code})
    async with asyncio.timeout(120):
        await queue.submit(run_id)
    return get_run(engine, run_id)


async def test_grade_solution_passes_with_waveform(
    docker_settings: Settings, engine: Engine
) -> None:
    run = await grade_code(docker_settings, engine, (COUNTER / "solution.v").read_text())

    assert run.status == RunStatus.succeeded, run.error
    assert run.result is not None
    assert run.result["status"] == "pass"
    assert len(run.result["tests"]) == 3
    wave = docker_settings.runs_dir / run.id / run.result["wave_file"]
    assert wave.is_file() and wave.stat().st_size > 0
    assert run.result["lint"] == []


async def test_grade_starter_fails(docker_settings: Settings, engine: Engine) -> None:
    run = await grade_code(docker_settings, engine, (COUNTER / "starter.v").read_text())

    assert run.status == RunStatus.succeeded, run.error
    assert run.exit_code == 1
    assert run.result is not None and run.result["status"] == "fail"
    # Verilator lint ran in the same job: the starter never drives q (line 5).
    assert (5, "UNDRIVEN") in {(d["line"], d["code"]) for d in run.result["lint"]}


async def test_grade_compile_error_has_line_numbers(
    docker_settings: Settings, engine: Engine
) -> None:
    code = "module counter4(input clk, output q);\n  assign q = ;\nendmodule\n"
    run = await grade_code(docker_settings, engine, code)

    assert run.result is not None and run.result["status"] == "compile_error"
    diagnostics = run.result["diagnostics"]
    assert diagnostics, run.result["log"]
    # Icarus may report several messages for the same line.
    assert {d["line"] for d in diagnostics} == {2}
    assert all(d["severity"] == "error" for d in diagnostics)


async def test_grade_cannot_read_solution(docker_settings: Settings, engine: Engine) -> None:
    run = await grade_code(docker_settings, engine, PEEK_AT_SOLUTION)

    assert run.result is not None
    assert "PEEK fd=0" in run.result["log"]  # $fopen failed: content/ is not mounted
    solution = (COUNTER / "solution.v").read_text()
    assert "q <= q + 4'd1" in solution  # the marker below really is in the solution
    assert "q <= q + 4'd1" not in run.result["log"]


async def test_lint_project_reports_per_file(docker_settings: Settings, engine: Engine) -> None:
    files = {
        "src/top.v": (
            "module top (input wire clk, input wire [3:0] a, output wire [1:0] y);\n"
            "  helper h (.a(a), .y(y));\n"
            "endmodule\n"
        ),
        "src/sub/helper.v": (
            '`include "widths.vh"\n'
            "module helper (input wire [3:0] a, output reg [`W-1:0] y);\n"
            "  always @(*) y = a;\n"
            "endmodule\n"
        ),
        "src/sub/widths.vh": "`define W 2\n",
    }
    params = {"top": "top", "sources": ["src/top.v", "src/sub/helper.v"]}
    run_id = new_run(engine, "lint", params)
    write_snapshot(docker_settings.runs_dir / run_id / "project", files)

    async with asyncio.timeout(120):
        await make_queue(docker_settings, engine).submit(run_id)

    run = get_run(engine, run_id)
    assert run.status == RunStatus.succeeded, run.error
    assert run.result is not None
    found = {(d["file"], d["line"], d["code"]) for d in run.result["diagnostics"]}
    # The include next to helper.v was found (no error), and both files were linted.
    assert run.result["errors"] == 0, run.result
    assert ("src/sub/helper.v", 3, "WIDTHTRUNC") in found
    assert ("src/top.v", 1, "UNUSEDSIGNAL") in found


async def test_lint_syntax_error_is_a_result(docker_settings: Settings, engine: Engine) -> None:
    run_id = new_run(engine, "lint", {"top": "broken", "sources": ["broken.v"]})
    write_snapshot(
        docker_settings.runs_dir / run_id / "project",
        {"broken.v": "module broken (input wire a, output wire y);\n  assign y = a\nendmodule\n"},
    )

    async with asyncio.timeout(120):
        await make_queue(docker_settings, engine).submit(run_id)

    run = get_run(engine, run_id)
    assert run.status == RunStatus.succeeded, run.error
    assert run.exit_code == 1
    assert run.result is not None and run.result["errors"] == 1
    assert run.result["diagnostics"][0]["line"] == 3


FIFO = Path(__file__).parents[1] / "fixtures" / "projects" / "fifo"


def project_files(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
        for p in root.rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize("simulator", ["icarus", "verilator"])
async def test_sim_fifo_with_scoreboard_passes(
    docker_settings: Settings, engine: Engine, simulator: str
) -> None:
    """Phase 2 criterion: a FIFO with a cocotb scoreboard is green on both simulators."""
    params = {
        "top": "fifo",
        "sources": ["src/fifo.v"],
        "tests": ["test/test_fifo.py"],
        "simulator": simulator,
        "parameters": {"DEPTH": 8},
    }
    run_id = new_run(engine, "sim", params)
    write_snapshot(docker_settings.runs_dir / run_id / "project", project_files(FIFO))

    async with asyncio.timeout(180):
        await make_queue(docker_settings, engine).submit(run_id)

    run = get_run(engine, run_id)
    assert run.status == RunStatus.succeeded, run.error
    assert run.result is not None
    assert run.result["status"] == "pass", run.result["tests"] or run.result["log"][-2000:]
    assert run.result["simulator"] == simulator
    # DEPTH from the params reached the design (the fill test checks it).
    assert len(run.result["tests"]) == 3
    wave = docker_settings.runs_dir / run_id / run.result["wave_file"]
    assert wave.is_file() and wave.stat().st_size > 0


async def test_sim_string_parameter_reaches_icarus(
    docker_settings: Settings, engine: Engine
) -> None:
    files = {
        "src/const_out.v": (
            "module const_out #(parameter [7:0] INIT = 8'h00) (output wire [7:0] q);\n"
            "  assign q = INIT;\nendmodule\n"
        ),
        "test/test_const.py": (
            "import cocotb\nfrom cocotb.triggers import Timer\n\n\n@cocotb.test()\n"
            "async def init_value(dut):\n    await Timer(1, unit='ns')\n"
            "    assert int(dut.q.value) == 0xA5, hex(int(dut.q.value))\n"
        ),
    }
    params = {
        "top": "const_out",
        "sources": ["src/const_out.v"],
        "tests": ["test/test_const.py"],
        "simulator": "icarus",
        "parameters": {"INIT": "8'hA5"},
    }
    run_id = new_run(engine, "sim", params)
    write_snapshot(docker_settings.runs_dir / run_id / "project", files)

    async with asyncio.timeout(120):
        await make_queue(docker_settings, engine).submit(run_id)

    run = get_run(engine, run_id)
    assert run.result is not None and run.result["status"] == "pass", run.result


PIPE_REG = Path(__file__).parents[1] / "fixtures" / "projects" / "pipe_reg"


@pytest.mark.parametrize(
    ("simulator", "broken"),
    [("icarus", False), ("verilator", False), ("icarus", True), ("verilator", True)],
)
async def test_snippets_make_a_working_testbench(
    docker_settings: Settings, engine: Engine, simulator: str, broken: bool
) -> None:
    """All cocotb snippets together test a valid/ready register on both simulators,
    and the scoreboard catches a register that drops data under backpressure."""
    snippets = load_snippets(REPO_ROOT / "content" / "snippets")
    design = (PIPE_REG / "src" / "pipe_reg.v").read_text(encoding="utf-8")
    if broken:  # ignores in_ready: overwrites the output while it is still waiting
        design = design.replace("end else if (in_ready) begin", "end else begin")
    params = {
        "top": "pipe_reg",
        "sources": ["src/pipe_reg.v"],
        "tests": ["test/test_pipe.py"],
        "simulator": simulator,
    }
    run_id = new_run(engine, "sim", params)
    write_snapshot(
        docker_settings.runs_dir / run_id / "project",
        {"src/pipe_reg.v": design, "test/test_pipe.py": assemble(snippets)},
    )

    async with asyncio.timeout(180):
        await make_queue(docker_settings, engine).submit(run_id)

    run = get_run(engine, run_id)
    assert run.status == RunStatus.succeeded, run.error
    assert run.result is not None
    (test,) = run.result["tests"]
    if broken:
        assert run.result["status"] == "fail"
        assert "seharusnya" in test["message"], test["message"]
    else:
        assert run.result["status"] == "pass", test["message"] or run.result["log"][-2000:]


def test_every_board_has_a_blinky_fixture() -> None:
    assert BOARDS
    for board_id in BOARDS:
        assert (BOARD_FIXTURES / board_id / "blinky.v").is_file(), board_id


@pytest.mark.parametrize("board_id", sorted(BOARDS))
async def test_board_profile_builds_blinky(
    docker_settings: Settings, engine: Engine, board_id: str
) -> None:
    """The tool arguments in a board profile work with the pinned toolchain."""
    run_id = new_run(engine, "board_check", {"board": board_id})

    async with asyncio.timeout(180):
        await make_queue(docker_settings, engine).submit(run_id)

    run = get_run(engine, run_id)
    run_dir = docker_settings.runs_dir / run_id
    log = (run_dir / "run.log").read_text(encoding="utf-8", errors="replace")
    assert run.status == RunStatus.succeeded, f"{run.error}\n{log[-3000:]}"
    board = BOARDS[board_id].board
    assert (run_dir / board.bitstream_file).stat().st_size > 0
    report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    # The template's clock pin carries the only clock, and blinky easily meets it.
    [clock] = report["fmax"].values()
    assert clock["constraint"] == board.clock.freq_mhz
    assert clock["achieved"] > clock["constraint"]
    for types in board.resources.values():
        assert all(t in report["utilization"] for t in types), types


BLINKY = Path(__file__).parents[1] / "fixtures" / "projects" / "blinky"
FPGA_PARAMS = {
    "top": "blinky",
    "sources": ["src/blinky.v"],
    "board": "tang-nano-9k",
    "constraints": "constraints/tang-nano-9k.cst",
    "freq_mhz": 27,
}


async def run_fpga(settings: Settings, engine: Engine, files: dict[str, str], **params: Any) -> Run:
    run_id = new_run(engine, "fpga", {**FPGA_PARAMS, **params})
    write_snapshot(settings.runs_dir / run_id / "project", files)
    async with asyncio.timeout(180):
        await make_queue(settings, engine).submit(run_id)
    run = get_run(engine, run_id)
    assert run.status == RunStatus.succeeded, run.error
    assert run.result is not None
    return run


async def test_fpga_blinky_builds_a_bitstream(docker_settings: Settings, engine: Engine) -> None:
    run = await run_fpga(docker_settings, engine, project_files(BLINKY))

    result = run.result
    assert result is not None
    assert result["status"] == "ok", result
    assert [(s["id"], s["status"]) for s in result["stages"]] == [
        ("synth", "ok"),
        ("pnr", "ok"),
        ("pack", "ok"),
    ]
    run_dir = docker_settings.runs_dir / run.id
    assert result["bitstream_url"] == f"/api/runs/{run.id}/files/build/bitstream.fs"
    assert (run_dir / "build" / "bitstream.fs").stat().st_size > 0
    assert result["versions"]["yosys"].startswith("Yosys ")
    assert "nextpnr" in result["versions"]["nextpnr"]
    report = json.loads((run_dir / "build" / "report.json").read_text(encoding="utf-8"))
    assert report["fmax"]  # the report the next task parses
    assert (run_dir / "build" / "stat.json").is_file()
    log = (run_dir / "run.log").read_text(encoding="utf-8")
    assert "==> Synthesize" in log and "==> Pack" in log
    assert "Numpy" not in log  # Apicula's start-up warnings are silenced


async def test_fpga_parameters_and_defines_reach_yosys(
    docker_settings: Settings, engine: Engine
) -> None:
    """Without W = 6 the LED bus has pins the template does not pin (PnR fails), and
    without ON the source does not parse (synthesis fails): both must reach Yosys."""
    design = "".join(
        [
            "module blinky #(parameter W = 8) (input wire clk, output wire [W-1:0] led);\n",
            "`ifndef ON\n  this is not verilog\n`endif\n",
            "  assign led = {W{1'b1}};\nendmodule\n",
        ]
    )
    files = {
        "src/blinky.v": design,
        "constraints/tang-nano-9k.cst": project_files(BLINKY)["constraints/tang-nano-9k.cst"],
    }

    built = await run_fpga(docker_settings, engine, files, parameters={"W": 6}, defines={"ON": 1})
    no_define = await run_fpga(docker_settings, engine, files, parameters={"W": 6})
    no_param = await run_fpga(docker_settings, engine, files, defines={"ON": 1})

    assert built.result is not None and built.result["status"] == "ok", built.result
    assert no_define.result is not None and no_define.result["stages"][0]["status"] == "failed"
    assert no_param.result is not None and "Unconstrained IO" in no_param.result["error"]


async def test_fpga_syntax_error_fails_synthesis_with_a_line(
    docker_settings: Settings, engine: Engine
) -> None:
    files = project_files(BLINKY)
    files["src/blinky.v"] = files["src/blinky.v"].replace("count = 0;", "count")

    run = await run_fpga(docker_settings, engine, files)

    result = run.result
    assert result is not None
    assert result["status"] == "failed"
    assert [s["status"] for s in result["stages"]] == ["failed", "skipped", "skipped"]
    [diag] = result["diagnostics"]
    assert diag["file"] == "src/blinky.v" and diag["line"] == 7
    assert "syntax error" in diag["message"]
    assert result["bitstream_url"] is None


async def test_fpga_unconstrained_pin_fails_place_and_route(
    docker_settings: Settings, engine: Engine
) -> None:
    files = project_files(BLINKY)
    cst = files["constraints/tang-nano-9k.cst"]
    files["constraints/tang-nano-9k.cst"] = cst.replace('IO_LOC "led[5]" 16;', "")

    run = await run_fpga(docker_settings, engine, files)

    result = run.result
    assert result is not None
    assert [s["status"] for s in result["stages"]] == ["ok", "failed", "skipped"]
    assert "Unconstrained IO" in result["error"]
    assert result["stages"][1]["log_url"].endswith("/build/nextpnr.log")


async def test_fpga_report_warns_about_a_latch(docker_settings: Settings, engine: Engine) -> None:
    """Phase 3 criterion: an accidental latch gives a clear warning in the result."""
    files = project_files(BLINKY)
    files["src/blinky.v"] = (
        "module blinky (input wire clk, input wire rst_n, output reg [5:0] led);\n"
        "    reg [5:0] count = 0;\n"
        "    always @(posedge clk) count <= count + 1'b1;\n"
        "    always @* begin\n"
        "        if (rst_n) led = count;\n"
        "    end\n"
        "endmodule\n"
    )

    run = await run_fpga(docker_settings, engine, files)

    assert run.result is not None
    [latch] = [w for w in run.result["warnings"] if w["kind"] == "latch"]
    assert (latch["signal"], latch["file"], latch["line"]) == ("led", "src/blinky.v", 4)


async def test_fpga_report_flags_missed_timing(docker_settings: Settings, engine: Engine) -> None:
    """Phase 3 criterion: a design that misses timing is marked, with its critical path."""
    run = await run_fpga(docker_settings, engine, project_files(BLINKY), freq_mhz=400)

    result = run.result
    assert result is not None
    assert result["status"] == "ok" and result["bitstream_url"]  # still packed
    assert result["timing_met"] is False
    [clock] = result["clocks"]
    assert clock["name"] == "clk" and clock["target_mhz"] == 400 and not clock["met"]
    assert result["critical_paths"][0]["steps"]
    assert {r["label"] for r in result["utilization"]} == {"LUT", "FF", "BRAM", "IO"}


def lesson_modules(*names: str) -> dict[str, str]:
    """Verilog blocks of lessons, one file per module (src/<module>.v)."""
    files = {}
    for name in names:
        text = (REPO_ROOT / "content" / "lessons" / f"{name}.md").read_text(encoding="utf-8")
        for block in text.split("```verilog\n")[1:]:
            code = block.split("```")[0]
            module = code.split("module ", 1)[1].split()[0]
            files[f"src/{module}.v"] = code
    return files


async def test_lesson_code_builds_for_the_board(docker_settings: Settings, engine: Engine) -> None:
    """The synchronizer and debounce code in the step 3 lessons builds cleanly."""
    files = lesson_modules("03-synchronizer", "03-debounce")
    assert sorted(files) == ["src/debounce.v", "src/sync2.v", "src/top.v"]
    sources = sorted(files)
    files["constraints/tang-nano-9k.cst"] = project_files(BLINKY)["constraints/tang-nano-9k.cst"]

    run = await run_fpga(docker_settings, engine, files, top="top", sources=sources)

    result = run.result
    assert result is not None
    assert result["status"] == "ok", result["error"]
    assert result["timing_met"] is True
    assert result["warnings"] == []


FPGA_TEMPLATES = ["fpga-blinky", "fpga-counter-led", "fpga-button", "fpga-de1-soc-blinky"]
# One plausible mistake per example; its testbench must catch it.
TEMPLATE_MUTANTS = {
    "fpga-blinky": ("src/blinky.v", "HALF_PERIOD[W-1:0] - 1'b1", "HALF_PERIOD[W-1:0]"),
    "fpga-counter-led": ("src/counter_led.v", "if (!run) begin", "if (1'b0) begin"),
    "fpga-de1-soc-blinky": ("src/de1_blinky.v", "on ^ SW[0]", "on"),
    "fpga-button": (
        "src/button_counter.v",
        "debounce #(.CYCLES(DEBOUNCE_CYCLES)) u_db (.clk(clk), .noisy(btn_sync), .clean(pressed));",
        "assign pressed = btn_sync;",
    ),
}


def template_files(template_id: str) -> dict[str, str]:
    [template] = [
        t for t in load_templates(REPO_ROOT / "content" / "templates") if t.id == template_id
    ]
    return template.files()


async def run_template(
    settings: Settings, engine: Engine, kind: str, files: dict[str, str], **override: Any
) -> Run:
    params = {**run_params(kind, files, {b: p.board for b, p in BOARDS.items()}), **override}
    run_id = new_run(engine, kind, params)
    write_snapshot(settings.runs_dir / run_id / "project", files)
    async with asyncio.timeout(240):
        await make_queue(settings, engine).submit(run_id)
    run = get_run(engine, run_id)
    assert run.status == RunStatus.succeeded, run.error
    assert run.result is not None
    return run


@pytest.mark.parametrize("simulator", ["icarus", "verilator"])
@pytest.mark.parametrize("template_id", FPGA_TEMPLATES)
async def test_fpga_template_simulates(
    docker_settings: Settings, engine: Engine, template_id: str, simulator: str
) -> None:
    """The example's testbench passes as shipped, on both simulators."""
    run = await run_template(
        docker_settings, engine, "sim", template_files(template_id), simulator=simulator
    )
    result = run.result
    assert result is not None
    assert result["status"] == "pass", result["tests"] or result["log"][-2000:]


@pytest.mark.parametrize("template_id", FPGA_TEMPLATES)
async def test_fpga_template_testbench_catches_a_mistake(
    docker_settings: Settings, engine: Engine, template_id: str
) -> None:
    files = template_files(template_id)
    path, old, new = TEMPLATE_MUTANTS[template_id]
    assert old in files[path]
    files[path] = files[path].replace(old, new)

    run = await run_template(docker_settings, engine, "sim", files)

    assert run.result is not None and run.result["status"] == "fail", run.result


@pytest.mark.parametrize("template_id", FPGA_TEMPLATES)
async def test_fpga_template_builds_cleanly(
    docker_settings: Settings, engine: Engine, template_id: str
) -> None:
    """The example builds for its board with the board-only parameters, meets
    timing, and has nothing to warn about."""
    files = template_files(template_id)
    run = await run_template(docker_settings, engine, "fpga", files)

    result = run.result
    assert result is not None
    assert result["status"] == "ok", result["error"]
    assert result["timing_met"] is True
    assert result["warnings"] == []
    [clock] = result["clocks"]
    board = BOARDS[run.params["board"]].board
    # Named after the top port, also through Cyclone V's clock buffers.
    assert clock["name"] == board.clock.port
    assert clock["target_mhz"] == board.clock.freq_mhz
    script = (docker_settings.runs_dir / run.id / "build" / "synth.ys").read_text("utf-8")
    assert "chparam -set" in script and "-set HALF_PERIOD 4 " not in script
