import asyncio
import json
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import Engine
from sqlmodel import Session

from app.config import Settings
from app.db import init_db, make_engine
from app.jobs.events import EventHub
from app.jobs.fake_runner import FakeJob, FakeRunner
from app.jobs.kinds import KINDS
from app.jobs.queue import JobQueue
from app.jobs.runner import ContainerSpec, JobClass
from app.models import Run, RunStatus

FIXTURES = Path(__file__).parent / "fixtures" / "runs"


def make_kind(job_class: JobClass, collect: Any = None) -> SimpleNamespace:
    return SimpleNamespace(
        JOB_CLASS=job_class,
        prepare=lambda run_dir, params: ContainerSpec(command=["true"], job_class=job_class),
        collect=collect or (lambda run_dir: {"ok": True}),
    )


TEST_KINDS = {
    **KINDS,
    "light": make_kind(JobClass.light),
    "heavy": make_kind(JobClass.heavy),
}


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = make_engine("sqlite://")
    init_db(engine)
    yield engine
    engine.dispose()


def make_queue(
    settings: Settings, engine: Engine, runner: FakeRunner, **overrides: Any
) -> tuple[JobQueue, EventHub]:
    settings = settings.model_copy(update=overrides)
    events = EventHub()
    queue = JobQueue(
        runner=runner, settings=settings, engine=engine, events=events, kinds=TEST_KINDS
    )
    return queue, events


def new_run(engine: Engine, kind: str = "echo", params: dict[str, Any] | None = None) -> str:
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


async def test_successful_run(settings: Settings, engine: Engine) -> None:
    runner = FakeRunner(FakeJob(logs=["Yosys 0.70+219 (git sha1 5053d0e26)", "done"]))
    queue, _ = make_queue(settings, engine, runner, oss_cad_suite_date="2026-10-24")
    run_id = new_run(engine)

    await queue.submit(run_id)

    run = get_run(engine, run_id)
    assert run.status == RunStatus.succeeded
    assert run.exit_code == 0
    assert run.error is None
    assert run.result == {"yosys_version": "Yosys 0.70+219 (git sha1 5053d0e26)"}
    assert run.tool_versions == {
        "image": "fake:image",
        "image_id": None,
        "oss_cad_suite": "2026-10-24",
    }
    assert run.started_at is not None and run.finished_at is not None
    log = (settings.runs_dir / run_id / "run.log").read_bytes()
    assert log == b"Yosys 0.70+219 (git sha1 5053d0e26)\ndone\n"
    assert runner.cleaned == {run_id}


async def test_result_files_from_fixture_are_collected(settings: Settings, engine: Engine) -> None:
    TEST_KINDS["json"] = make_kind(
        JobClass.light, collect=lambda run_dir: json.loads((run_dir / "result.json").read_text())
    )
    runner = FakeRunner(FakeJob(fixture_dir=FIXTURES / "json-result"))
    queue, _ = make_queue(settings, engine, runner)
    run_id = new_run(engine, kind="json")

    await queue.submit(run_id)

    assert get_run(engine, run_id).result == {"status": "pass", "tests": 3}


async def test_nonzero_exit_marks_failed(settings: Settings, engine: Engine) -> None:
    queue, _ = make_queue(settings, engine, FakeRunner(FakeJob(exit_code=3)))
    run_id = new_run(engine)

    await queue.submit(run_id)

    run = get_run(engine, run_id)
    assert run.status == RunStatus.failed
    assert run.exit_code == 3
    assert run.error is not None and "3" in run.error


async def test_timeout_kills_container(settings: Settings, engine: Engine) -> None:
    runner = FakeRunner(FakeJob(block=True))
    queue, _ = make_queue(settings, engine, runner, job_light_timeout_s=0.05)
    run_id = new_run(engine)

    await queue.submit(run_id)

    run = get_run(engine, run_id)
    assert run.status == RunStatus.timeout
    assert run.error is not None and "batas waktu" in run.error
    assert runner.killed == {run_id}
    assert runner.cleaned == {run_id}


async def test_cancel_running_job(settings: Settings, engine: Engine) -> None:
    runner = FakeRunner(FakeJob(block=True))
    queue, _ = make_queue(settings, engine, runner)
    run_id = new_run(engine)

    task = queue.submit(run_id)
    await runner.wait_started(1)
    assert await queue.cancel(run_id) is True
    await task

    run = get_run(engine, run_id)
    assert run.status == RunStatus.cancelled
    assert runner.killed == {run_id}
    assert runner.cleaned == {run_id}


async def test_cancel_queued_job_never_starts(settings: Settings, engine: Engine) -> None:
    runner = FakeRunner(FakeJob(block=True))
    queue, _ = make_queue(settings, engine, runner, job_light_concurrency=1)
    first, second = new_run(engine), new_run(engine)

    t1, t2 = queue.submit(first), queue.submit(second)
    await runner.wait_started(1)
    assert await queue.cancel(second) is True
    await t2
    runner.release(first)
    await t1

    assert get_run(engine, second).status == RunStatus.cancelled
    assert get_run(engine, first).status == RunStatus.succeeded
    assert [run_id for run_id, _ in runner.started] == [first]


async def test_cancel_while_container_is_starting(settings: Settings, engine: Engine) -> None:
    gate = asyncio.Event()
    runner = FakeRunner(FakeJob(block=True), start_gate=gate)
    queue, _ = make_queue(settings, engine, runner)
    run_id = new_run(engine)

    task = queue.submit(run_id)
    await runner.wait_started(1)  # inside start(), container not returned yet
    assert await queue.cancel(run_id) is True
    gate.set()
    async with asyncio.timeout(2):  # without the kill the blocked job would hang forever
        await task

    assert get_run(engine, run_id).status == RunStatus.cancelled
    assert runner.killed == {run_id}
    assert runner.cleaned == {run_id}


async def test_cancel_unknown_run(settings: Settings, engine: Engine) -> None:
    queue, _ = make_queue(settings, engine, FakeRunner())
    assert await queue.cancel("nope") is False


async def test_light_concurrency_is_limited(settings: Settings, engine: Engine) -> None:
    runner = FakeRunner(FakeJob(block=True))
    queue, _ = make_queue(settings, engine, runner, job_light_concurrency=2)
    run_ids = [new_run(engine, kind="light") for _ in range(5)]

    tasks = [queue.submit(r) for r in run_ids]
    for done in range(5):
        await runner.wait_started(min(done + 2, 5))
        await asyncio.sleep(0.02)
        assert len(runner.running) <= 2
        runner.release(runner.started[done][0])
    await asyncio.gather(*tasks)

    assert runner.max_running == 2
    assert all(get_run(engine, r).status == RunStatus.succeeded for r in run_ids)


async def test_light_and_heavy_queues_are_independent(settings: Settings, engine: Engine) -> None:
    runner = FakeRunner(FakeJob(block=True))
    queue, _ = make_queue(
        settings, engine, runner, job_light_concurrency=1, job_heavy_concurrency=1
    )
    light, heavy = new_run(engine, kind="light"), new_run(engine, kind="heavy")

    tasks = [queue.submit(light), queue.submit(heavy)]
    await runner.wait_started(2)
    assert runner.running == {light, heavy}
    runner.release(light)
    runner.release(heavy)
    await asyncio.gather(*tasks)


async def test_collect_error_marks_failed(settings: Settings, engine: Engine) -> None:
    def broken(run_dir: Path) -> dict[str, Any]:
        raise ValueError("result.json rusak")

    TEST_KINDS["broken"] = make_kind(JobClass.light, collect=broken)
    queue, _ = make_queue(settings, engine, FakeRunner())
    run_id = new_run(engine, kind="broken")

    await queue.submit(run_id)

    run = get_run(engine, run_id)
    assert run.status == RunStatus.failed
    assert run.error is not None and "result.json rusak" in run.error


async def test_invalid_params_mark_failed(settings: Settings, engine: Engine) -> None:
    runner = FakeRunner()
    queue, _ = make_queue(settings, engine, runner)
    run_id = new_run(engine, params={"sleep_s": -5})

    await queue.submit(run_id)

    assert get_run(engine, run_id).status == RunStatus.failed
    assert runner.started == []


async def test_events_are_published(settings: Settings, engine: Engine) -> None:
    queue, events = make_queue(settings, engine, FakeRunner(FakeJob(logs=["hello"])))
    run_id = new_run(engine)

    async with events.subscribe(run_id) as inbox:
        await queue.submit(run_id)
        received = [inbox.get_nowait() for _ in range(inbox.qsize())]

    assert received == [
        {"type": "status", "status": "running"},
        {"type": "log", "line": "hello"},
        {"type": "status", "status": "succeeded"},
    ]


async def test_shutdown_kills_running_jobs(settings: Settings, engine: Engine) -> None:
    runner = FakeRunner(FakeJob(block=True))
    queue, _ = make_queue(settings, engine, runner)
    run_id = new_run(engine)

    queue.submit(run_id)
    await runner.wait_started(1)
    await queue.shutdown()

    assert runner.killed == {run_id}
    # Left as "running" on purpose: startup recovery marks it failed with a reason.
    assert get_run(engine, run_id).status == RunStatus.running
