"""End-to-end job tests against the real Docker daemon and toolchain image.

Skipped by default. Run with: SMARTX_DOCKER_TESTS=1 uv run pytest tests/integration
"""

import asyncio
import os
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import docker
import pytest
from sqlalchemy import Engine
from sqlmodel import Session

from app.config import REPO_ROOT, Settings
from app.db import init_db, make_engine
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
        prepare=lambda run_dir, params: ContainerSpec(command=["sh", "-c", SANDBOX_SCRIPT]),
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
        kinds=KINDS_UNDER_TEST,
    )


def new_run(engine: Engine, kind: str, params: dict[str, int] | None = None) -> str:
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
