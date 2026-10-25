"""Replay a run's history, then follow live events until the run ends."""

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy import Engine
from sqlmodel import Session

from app.jobs.events import Event, EventHub
from app.models import Run, RunStatus

TERMINAL_STATUSES = frozenset(
    {RunStatus.succeeded, RunStatus.failed, RunStatus.cancelled, RunStatus.timeout}
)


async def follow_run(
    run_id: str, *, engine: Engine, events: EventHub, run_dir: Path
) -> AsyncIterator[Event]:
    """Yield every log line and status change exactly once.

    The queue writes a log line to run.log and publishes it in one synchronous step, and
    updates the DB status right before publishing it. Subscribing, reading run.log and
    reading the status below also happen without an await in between, so each event is
    either in the snapshot or arrives in the inbox afterwards, never both.
    """
    async with events.subscribe(run_id) as inbox:
        log = run_dir / "run.log"
        lines = log.read_text(encoding="utf-8").splitlines() if log.is_file() else []
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run is None:
                return
            status = run.status

        for line in lines:
            yield {"type": "log", "line": line}
        yield {"type": "status", "status": status.value}
        if status in TERMINAL_STATUSES:
            return

        while True:
            event = await inbox.get()
            yield event
            if event["type"] == "status" and event["status"] in TERMINAL_STATUSES:
                return
