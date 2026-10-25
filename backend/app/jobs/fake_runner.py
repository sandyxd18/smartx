"""In-memory JobRunner for unit tests. No Docker involved."""

import asyncio
import shutil
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from pathlib import Path

from app.jobs.runner import ContainerSpec, JobHandle, JobRunner

KILLED_EXIT_CODE = 137


@dataclass
class FakeJob:
    logs: list[str] = field(default_factory=list)
    exit_code: int = 0
    # Copied into the run folder when the job exits normally (e.g. a result.json fixture).
    fixture_dir: Path | None = None
    # Keep "running" until release() or kill() is called.
    block: bool = False


@dataclass
class _State:
    job: FakeJob
    run_dir: Path
    done: asyncio.Event = field(default_factory=asyncio.Event)
    exit_code: int | None = None


class FakeRunner(JobRunner):
    def __init__(
        self,
        job: FakeJob | Callable[[str, ContainerSpec], FakeJob] | None = None,
        start_gate: asyncio.Event | None = None,
    ):
        self._job_for = job if callable(job) else (lambda _id, _spec: job or FakeJob())
        # When set, start() blocks until the event is set (simulates a slow image start).
        self._start_gate = start_gate
        self._states: dict[str, _State] = {}
        self.started: list[tuple[str, ContainerSpec]] = []
        self.running: set[str] = set()
        self.max_running = 0
        self.killed: set[str] = set()
        self.cleaned: set[str] = set()
        self.orphans_removed = 0

    async def start(self, run_id: str, run_dir: Path, spec: ContainerSpec) -> JobHandle:
        job = self._job_for(run_id, spec)
        state = _State(job=job, run_dir=run_dir)
        self._states[run_id] = state
        self.started.append((run_id, spec))
        if self._start_gate is not None:
            await self._start_gate.wait()
        self.running.add(run_id)
        self.max_running = max(self.max_running, len(self.running))
        if not job.block:
            self._finish(state, job.exit_code)
        return JobHandle(run_id=run_id, container_id=f"fake-{run_id}", image="fake:image")

    async def stream_logs(self, handle: JobHandle) -> AsyncIterator[str]:
        state = self._states[handle.run_id]
        for line in state.job.logs:
            yield line
        await state.done.wait()

    async def wait(self, handle: JobHandle) -> int:
        state = self._states[handle.run_id]
        await state.done.wait()
        self.running.discard(handle.run_id)
        assert state.exit_code is not None
        return state.exit_code

    async def kill(self, handle: JobHandle) -> None:
        self.killed.add(handle.run_id)
        state = self._states[handle.run_id]
        if not state.done.is_set():
            state.exit_code = KILLED_EXIT_CODE
            state.done.set()

    async def cleanup(self, handle: JobHandle) -> None:
        self.cleaned.add(handle.run_id)

    async def remove_orphans(self) -> int:
        self.orphans_removed += 1
        return 0

    def release(self, run_id: str) -> None:
        """Let a blocked job exit normally."""
        state = self._states[run_id]
        self._finish(state, state.job.exit_code)

    async def wait_started(self, count: int, timeout: float = 2.0) -> None:
        async with asyncio.timeout(timeout):
            while len(self.started) < count:
                await asyncio.sleep(0.01)

    def _finish(self, state: _State, exit_code: int) -> None:
        if state.done.is_set():
            return
        if state.job.fixture_dir is not None:
            shutil.copytree(state.job.fixture_dir, state.run_dir, dirs_exist_ok=True)
        state.exit_code = exit_code
        state.done.set()
