"""Two in-process job queues (light/heavy) with per-class concurrency, timeout and cancel."""

import asyncio
import contextlib
import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy import Engine
from sqlmodel import Session

from app.config import Settings
from app.jobs.context import JobContext, JobInputError
from app.jobs.events import EventHub
from app.jobs.kinds import KINDS, JobKind
from app.jobs.runner import ContainerSpec, JobClass, JobHandle, JobRunner
from app.models import Run, RunStatus, utcnow

log = logging.getLogger(__name__)

# How long to keep draining logs after the container exited.
LOG_DRAIN_TIMEOUT_S = 10


class _Phase(Enum):
    queued = "queued"
    starting = "starting"
    running = "running"


@dataclass
class _Active:
    task: "asyncio.Task[None] | None" = None
    phase: _Phase = _Phase.queued
    handle: JobHandle | None = None
    cancel_requested: bool = False


@dataclass
class _Outcome:
    status: RunStatus
    exit_code: int | None = None
    error: str | None = None
    result: dict[str, Any] | None = field(default=None)


class JobQueue:
    def __init__(
        self,
        *,
        runner: JobRunner,
        settings: Settings,
        engine: Engine,
        events: EventHub,
        context: JobContext,
        kinds: Mapping[str, JobKind] = KINDS,
        on_finished: Callable[[str], None] | None = None,
    ) -> None:
        self._runner = runner
        self._context = context
        # Called with the run id after the final status is stored, before it is published.
        self._on_finished = on_finished
        self._settings = settings
        self._engine = engine
        self._events = events
        self._kinds = kinds
        self._slots = {
            JobClass.light: asyncio.Semaphore(settings.job_light_concurrency),
            JobClass.heavy: asyncio.Semaphore(settings.job_heavy_concurrency),
        }
        self._timeouts = {
            JobClass.light: settings.job_light_timeout_s,
            JobClass.heavy: settings.job_heavy_timeout_s,
        }
        self._active: dict[str, _Active] = {}

    def run_dir(self, run_id: str) -> Path:
        return self._settings.runs_dir / run_id

    def submit(self, run_id: str) -> "asyncio.Task[None]":
        """Schedule a run that already exists in the DB with status 'queued'."""
        active = _Active()
        self._active[run_id] = active
        active.task = asyncio.create_task(self._execute(run_id, active), name=f"run-{run_id}")
        active.task.add_done_callback(lambda _: self._active.pop(run_id, None))
        return active.task

    async def cancel(self, run_id: str) -> bool:
        active = self._active.get(run_id)
        if active is None:
            return False
        active.cancel_requested = True
        if active.phase is _Phase.queued and active.task is not None:
            active.task.cancel()
        elif active.phase is _Phase.running and active.handle is not None:
            await self._runner.kill(active.handle)
        # _Phase.starting: _execute kills the container as soon as start() returns.
        return True

    async def shutdown(self) -> None:
        """Kill everything in flight. Runs stay 'running'; startup recovery fails them."""
        actives = list(self._active.values())
        for active in actives:
            if active.task is not None:
                active.task.cancel()
        for active in actives:
            if active.handle is not None:
                with contextlib.suppress(Exception):
                    await self._runner.kill(active.handle)
        tasks = [a.task for a in actives if a.task is not None]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute(self, run_id: str, active: _Active) -> None:
        try:
            outcome = await self._execute_inner(run_id, active)
        except asyncio.CancelledError:
            if not active.cancel_requested:
                raise  # shutdown
            outcome = _Outcome(RunStatus.cancelled, error="Dibatalkan sebelum mulai.")
        except Exception as exc:
            log.exception("run %s crashed", run_id)
            outcome = _Outcome(RunStatus.failed, error=f"Kesalahan internal: {exc}")
        self._update(
            run_id,
            status=outcome.status,
            exit_code=outcome.exit_code,
            error=outcome.error,
            result=outcome.result,
            finished_at=utcnow(),
        )
        if self._on_finished is not None:
            try:
                self._on_finished(run_id)
            except Exception:
                log.exception("on_finished hook failed for run %s", run_id)
        self._events.publish(run_id, {"type": "status", "status": outcome.status.value})

    async def _execute_inner(self, run_id: str, active: _Active) -> _Outcome:
        run = self._load(run_id)
        kind = self._kinds.get(run.kind)
        if kind is None:
            return _Outcome(RunStatus.failed, error=f"Jenis job tidak dikenal: {run.kind}")

        async with self._slots[kind.JOB_CLASS]:
            active.phase = _Phase.starting
            run_dir = self.run_dir(run_id)
            run_dir.mkdir(parents=True, exist_ok=True)
            try:
                spec = kind.prepare(run_dir, run.params, self._context)
            except ValidationError as exc:
                return _Outcome(RunStatus.failed, error=f"Parameter tidak valid: {exc}")
            except JobInputError as exc:
                return _Outcome(RunStatus.failed, error=str(exc))

            self._update(run_id, status=RunStatus.running, started_at=utcnow())
            self._events.publish(run_id, {"type": "status", "status": RunStatus.running.value})

            handle = await self._runner.start(run_id, run_dir, spec)
            active.handle = handle
            active.phase = _Phase.running
            self._update(
                run_id,
                tool_versions={
                    "image": handle.image,
                    "image_id": handle.image_id,
                    "oss_cad_suite": self._settings.oss_cad_suite_date or None,
                },
            )
            try:
                return await self._supervise(run_id, run_dir, kind, spec, handle, active)
            finally:
                await self._runner.cleanup(handle)

    async def _supervise(
        self,
        run_id: str,
        run_dir: Path,
        kind: JobKind,
        spec: ContainerSpec,
        handle: JobHandle,
        active: _Active,
    ) -> _Outcome:
        if active.cancel_requested:  # cancel arrived while the container was starting
            await self._runner.kill(handle)

        timeout = spec.timeout_s or self._timeouts[kind.JOB_CLASS]
        pump = asyncio.create_task(self._pump_logs(run_id, run_dir, handle))
        timed_out = False
        exit_code: int | None = None
        try:
            try:
                exit_code = await asyncio.wait_for(self._runner.wait(handle), timeout)
            except TimeoutError:
                timed_out = True
                await self._runner.kill(handle)
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(asyncio.shield(pump), LOG_DRAIN_TIMEOUT_S)
        finally:
            if not pump.done():
                pump.cancel()

        if active.cancel_requested:
            return _Outcome(RunStatus.cancelled, exit_code, "Dibatalkan oleh pengguna.")
        if timed_out:
            return _Outcome(RunStatus.timeout, None, f"Melebihi batas waktu {timeout:g} detik.")
        try:
            result = kind.collect(run_dir)
        except Exception as exc:
            return _Outcome(RunStatus.failed, exit_code, f"Gagal membaca hasil run: {exc}")
        if exit_code not in kind.OK_EXIT_CODES:
            return _Outcome(
                RunStatus.failed, exit_code, f"Proses keluar dengan kode {exit_code}.", result
            )
        return _Outcome(RunStatus.succeeded, exit_code, None, result)

    async def _pump_logs(self, run_id: str, run_dir: Path, handle: JobHandle) -> None:
        # newline="\n": identical run.log on every host OS (no CRLF on Windows).
        with (run_dir / "run.log").open("w", encoding="utf-8", newline="\n") as out:
            async for line in self._runner.stream_logs(handle):
                out.write(line + "\n")
                out.flush()
                self._events.publish(run_id, {"type": "log", "line": line})

    def _load(self, run_id: str) -> Run:
        with Session(self._engine) as session:
            run = session.get(Run, run_id)
            if run is None:
                raise LookupError(f"run {run_id} tidak ada")
            return run

    def _update(self, run_id: str, **fields: Any) -> None:
        with Session(self._engine) as session:
            run = session.get(Run, run_id)
            if run is None:
                return
            for key, value in fields.items():
                setattr(run, key, value)
            session.add(run)
            session.commit()
