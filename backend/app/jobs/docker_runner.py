"""JobRunner backed by the Docker daemon. All container hardening lives here."""

import asyncio
import hashlib
import os
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import docker
from docker.errors import APIError, NotFound

from app.config import Settings
from app.jobs.runner import ContainerSpec, JobClass, JobHandle, JobRunner, LineSplitter
from app.paths import safe_join

RUN_LABEL = "smartx.run_id"
# Which SmartX installation started the container. Orphan cleanup only touches its own,
# so a dev backend and the test suite sharing one Docker daemon leave each other alone.
INSTANCE_LABEL = "smartx.instance"

ClientFactory = Callable[[float | None], Any]


def _default_client(timeout: float | None) -> Any:
    return docker.from_env(timeout=timeout)


def instance_id(settings: Settings) -> str:
    """Stable id of this installation, derived from where its data lives on the host."""
    where = settings.host_data_dir or str(settings.data_dir.resolve())
    return hashlib.sha256(where.encode()).hexdigest()[:16]


def _already_gone(exc: APIError) -> bool:
    # 404: removed; 409: "removal already in progress" (someone else is removing it).
    return isinstance(exc, NotFound) or exc.status_code == 409


# The 'smartx' user baked into the toolchain image.
FALLBACK_JOB_USER = "1000:1000"


def default_job_user() -> str:
    """The backend's own uid:gid, so run files belong to the person running SmartX.

    Falls back to the image user on Windows (no uids) and when the backend runs as root
    (e.g. inside its compose container): jobs must never run as root.
    """
    getuid = getattr(os, "getuid", None)
    if getuid is None or getuid() == 0:
        return FALLBACK_JOB_USER
    return f"{getuid()}:{os.getgid()}"


def _hand_over(run_dir: Path, user: str) -> None:
    """A root backend creates run dirs as root; give them to the non-root job user."""
    geteuid = getattr(os, "geteuid", None)
    if geteuid is not None and geteuid() == 0:
        uid, _, gid = user.partition(":")
        os.chown(run_dir, int(uid), int(gid))


def host_path(path: Path, local_root: Path, host_root: str) -> str:
    """Translate a path under local_root into the same path as the Docker host sees it."""
    if not host_root:
        return str(path)
    rel = path.resolve().relative_to(local_root.resolve())  # ValueError if outside
    base = host_root.rstrip("/\\")
    return base if rel == Path(".") else f"{base}/{rel.as_posix()}"


class DockerRunner(JobRunner):
    def __init__(self, settings: Settings, client_factory: ClientFactory = _default_client):
        self._settings = settings
        self._client_factory = client_factory
        self._api: Any = None
        self._stream_api: Any = None

    # Clients are created lazily: the backend must start even when Docker is down.
    def _client(self) -> Any:
        if self._api is None:
            self._api = self._client_factory(30)
        return self._api

    def _stream_client(self) -> Any:
        # No read timeout: logs/wait block as long as the job runs; the queue enforces limits.
        if self._stream_api is None:
            self._stream_api = self._client_factory(None)
        return self._stream_api

    def _run_kwargs(self, run_id: str, run_dir: Path, spec: ContainerSpec) -> dict[str, Any]:
        s = self._settings
        if spec.job_class is JobClass.heavy:
            image, memory, cpus = s.asic_image, s.job_heavy_memory, s.job_heavy_cpus
            if not image or image.endswith(":CHANGE_ME"):
                raise RuntimeError("ASIC_IMAGE belum diatur di .env")
        else:
            image, memory, cpus = s.toolchain_image, s.job_light_memory, s.job_light_cpus

        volumes = {host_path(run_dir, s.data_dir, s.host_data_dir): {"bind": "/work", "mode": "rw"}}
        for subdir, target in spec.readonly_subdirs.items():
            source = safe_join(run_dir, subdir)
            if not source.is_dir():
                raise RuntimeError(f"folder {subdir} tidak ada di folder run")
            volumes[host_path(source, s.data_dir, s.host_data_dir)] = {"bind": target, "mode": "ro"}
        if spec.mount_content:
            content = host_path(s.content_dir, s.content_dir, s.host_content_dir)
            volumes[content] = {"bind": "/content", "mode": "ro"}
        if spec.mount_tools:
            tools = host_path(s.tools_dir, s.tools_dir, s.host_tools_dir)
            volumes[tools] = {"bind": "/tools", "mode": "ro"}

        return {
            "image": image,
            "command": spec.command,
            "environment": spec.env,
            "detach": True,
            "network_mode": "none",
            "user": s.job_user or default_job_user(),
            "mem_limit": memory,
            "memswap_limit": memory,  # no swap on top of the memory limit
            "nano_cpus": int(cpus * 1_000_000_000),
            "pids_limit": s.job_pids_limit,
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges"],
            "working_dir": "/work",
            "volumes": volumes,
            "labels": {RUN_LABEL: run_id, INSTANCE_LABEL: instance_id(s)},
        }

    async def start(self, run_id: str, run_dir: Path, spec: ContainerSpec) -> JobHandle:
        kwargs = self._run_kwargs(run_id, run_dir, spec)
        _hand_over(run_dir, kwargs["user"])
        container = await asyncio.to_thread(self._client().containers.run, **kwargs)
        return JobHandle(
            run_id=run_id,
            container_id=container.id,
            image=kwargs["image"],
            image_id=getattr(container.image, "id", None),
        )

    async def stream_logs(self, handle: JobHandle) -> AsyncIterator[str]:
        container = await asyncio.to_thread(
            self._stream_client().containers.get, handle.container_id
        )
        stream = await asyncio.to_thread(
            container.logs, stream=True, follow=True, stdout=True, stderr=True
        )
        splitter = LineSplitter()
        while (chunk := await asyncio.to_thread(next, stream, None)) is not None:
            for line in splitter.feed(chunk):
                yield line
        for line in splitter.flush():
            yield line

    async def wait(self, handle: JobHandle) -> int:
        container = await asyncio.to_thread(
            self._stream_client().containers.get, handle.container_id
        )
        status = await asyncio.to_thread(container.wait)
        return int(status["StatusCode"])

    async def kill(self, handle: JobHandle) -> None:
        def _kill() -> None:
            try:
                self._client().containers.get(handle.container_id).kill()
            except NotFound:
                return
            except APIError as exc:
                if exc.status_code != 409:  # 409: container is not running
                    raise

        await asyncio.to_thread(_kill)

    async def cleanup(self, handle: JobHandle) -> None:
        def _remove() -> None:
            try:
                self._client().containers.get(handle.container_id).remove(force=True)
            except APIError as exc:
                if not _already_gone(exc):
                    raise

        await asyncio.to_thread(_remove)

    async def remove_orphans(self) -> int:
        def _remove_all() -> int:
            mine = [RUN_LABEL, f"{INSTANCE_LABEL}={instance_id(self._settings)}"]
            leftovers = self._client().containers.list(all=True, filters={"label": mine})
            removed = 0
            for container in leftovers:
                try:
                    container.remove(force=True)
                    removed += 1
                except APIError as exc:
                    if not _already_gone(exc):
                        raise
            return removed

        return await asyncio.to_thread(_remove_all)
