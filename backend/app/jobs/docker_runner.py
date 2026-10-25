"""JobRunner backed by the Docker daemon. All container hardening lives here."""

import asyncio
import contextlib
import os
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import docker
from docker.errors import APIError, NotFound

from app.config import Settings
from app.jobs.runner import ContainerSpec, JobClass, JobHandle, JobRunner, LineSplitter

RUN_LABEL = "smartx.run_id"

ClientFactory = Callable[[float | None], Any]


def _default_client(timeout: float | None) -> Any:
    return docker.from_env(timeout=timeout)


def default_job_user() -> str:
    if hasattr(os, "getuid"):
        return f"{os.getuid()}:{os.getgid()}"
    return "1000:1000"  # Windows host: the 'smartx' user baked into the toolchain image.


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
        if spec.mount_content:
            content = host_path(s.content_dir, s.content_dir, s.host_content_dir)
            volumes[content] = {"bind": "/content", "mode": "ro"}

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
            "labels": {RUN_LABEL: run_id},
        }

    async def start(self, run_id: str, run_dir: Path, spec: ContainerSpec) -> JobHandle:
        kwargs = self._run_kwargs(run_id, run_dir, spec)
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
            with contextlib.suppress(NotFound):
                self._client().containers.get(handle.container_id).remove(force=True)

        await asyncio.to_thread(_remove)

    async def remove_orphans(self) -> int:
        def _remove_all() -> int:
            leftovers = self._client().containers.list(all=True, filters={"label": RUN_LABEL})
            for container in leftovers:
                container.remove(force=True)
            return len(leftovers)

        return await asyncio.to_thread(_remove_all)
