"""End-to-end job tests against the real Docker daemon and toolchain image.

Skipped by default. Run with: SMARTX_DOCKER_TESTS=1 uv run pytest tests/integration
"""

import asyncio
import os
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
from app.db import init_db, make_engine
from app.jobs.context import JobContext
from app.jobs.docker_runner import RUN_LABEL, DockerRunner
from app.jobs.events import EventHub
from app.jobs.kinds import KINDS
from app.jobs.queue import JobQueue
from app.jobs.runner import ContainerSpec, JobClass
from app.models import Run, RunStatus

pytestmark = pytest.mark.skipif(
    os.environ.get("SMARTX_DOCKER_TESTS") != "1", reason="set SMARTX_DOCKER_TESTS=1"
)

SANDBOX_SCRIPT = (
    "echo uid=$(id -u); "
    "echo net=$(ls /sys/class/net | tr '\\n' ' '); "
    "touch /work/written && echo work=rw; "
    "touch /content/x 2>/dev/null && echo content=rw || echo content=ro"
)

KINDS_UNDER_TEST = {
    **KINDS,
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
