import asyncio
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine
from sqlmodel import Session

from app.config import Settings
from app.db import init_db, make_engine
from app.jobs.events import Event, EventHub
from app.jobs.fake_runner import FakeJob, FakeRunner
from app.jobs.queue import JobQueue
from app.jobs.stream import follow_run
from app.models import Run


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = make_engine("sqlite://")
    init_db(engine)
    yield engine
    engine.dispose()


def setup(
    settings: Settings, engine: Engine, runner: FakeRunner, **overrides: Any
) -> tuple[JobQueue, EventHub, Settings]:
    settings = settings.model_copy(update=overrides)
    events = EventHub()
    queue = JobQueue(runner=runner, settings=settings, engine=engine, events=events)
    return queue, events, settings


def new_run(engine: Engine) -> str:
    with Session(engine) as s:
        run = Run(kind="echo")
        s.add(run)
        s.commit()
        return run.id


async def collect(events: EventHub, engine: Engine, settings: Settings, run_id: str) -> list[Event]:
    run_dir = settings.runs_dir / run_id
    async with asyncio.timeout(2):
        return [e async for e in follow_run(run_id, engine=engine, events=events, run_dir=run_dir)]


async def test_finished_run_is_replayed(settings: Settings, engine: Engine) -> None:
    queue, events, settings = setup(settings, engine, FakeRunner(FakeJob(logs=["a", "b"])))
    run_id = new_run(engine)
    await queue.submit(run_id)

    assert await collect(events, engine, settings, run_id) == [
        {"type": "log", "line": "a"},
        {"type": "log", "line": "b"},
        {"type": "status", "status": "succeeded"},
    ]


async def test_running_run_replays_then_follows(settings: Settings, engine: Engine) -> None:
    runner = FakeRunner(FakeJob(logs=["a", "b"], block=True))
    queue, events, settings = setup(settings, engine, runner)
    run_id = new_run(engine)
    task = queue.submit(run_id)
    await runner.wait_started(1)
    await asyncio.sleep(0.05)  # let the log pump write "a" and "b"

    follower = asyncio.create_task(collect(events, engine, settings, run_id))
    await asyncio.sleep(0.05)
    runner.release(run_id)
    await task

    assert await follower == [
        {"type": "log", "line": "a"},
        {"type": "log", "line": "b"},
        {"type": "status", "status": "running"},
        {"type": "status", "status": "succeeded"},
    ]


async def test_queued_run_streams_everything_once(settings: Settings, engine: Engine) -> None:
    runner = FakeRunner(lambda run_id, spec: FakeJob(logs=[f"log {run_id[:4]}"], block=True))
    queue, events, settings = setup(settings, engine, runner, job_light_concurrency=1)
    first, second = new_run(engine), new_run(engine)
    t1, t2 = queue.submit(first), queue.submit(second)
    await runner.wait_started(1)

    follower = asyncio.create_task(collect(events, engine, settings, second))
    await asyncio.sleep(0.05)
    runner.release(first)
    await runner.wait_started(2)
    await asyncio.sleep(0.05)
    runner.release(second)
    await asyncio.gather(t1, t2)

    assert await follower == [
        {"type": "status", "status": "queued"},
        {"type": "status", "status": "running"},
        {"type": "log", "line": f"log {second[:4]}"},
        {"type": "status", "status": "succeeded"},
    ]
