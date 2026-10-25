"""JobRunner interface shared by the Docker runner and the fake runner used in tests."""

import abc
import codecs
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class JobClass(StrEnum):
    light = "light"  # toolchain image: grading, sim, lint, FPGA
    heavy = "heavy"  # ASIC image: LibreLane


@dataclass(frozen=True)
class ContainerSpec:
    """What a job kind wants to run. Image and limits come from the job class."""

    command: list[str]
    job_class: JobClass = JobClass.light
    env: dict[str, str] = field(default_factory=dict)
    mount_content: bool = True


@dataclass
class JobHandle:
    run_id: str
    container_id: str
    image: str
    image_id: str | None = None


class JobRunner(abc.ABC):
    @abc.abstractmethod
    async def start(self, run_id: str, run_dir: Path, spec: ContainerSpec) -> JobHandle:
        """Create and start the container; run_dir is mounted at /work."""

    @abc.abstractmethod
    def stream_logs(self, handle: JobHandle) -> AsyncIterator[str]:
        """Yield stdout+stderr lines (without newline) until the container exits."""

    @abc.abstractmethod
    async def wait(self, handle: JobHandle) -> int:
        """Block until the container exits and return its exit code."""

    @abc.abstractmethod
    async def kill(self, handle: JobHandle) -> None:
        """Stop the container immediately. Safe to call on an exited container."""

    @abc.abstractmethod
    async def cleanup(self, handle: JobHandle) -> None:
        """Remove the container. Safe to call more than once."""

    async def remove_orphans(self) -> int:
        """Remove job containers left over from a previous backend process."""
        return 0


class LineSplitter:
    """Turn a stream of byte chunks into text lines, tolerating split UTF-8 sequences."""

    def __init__(self) -> None:
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self._buffer = ""

    def feed(self, chunk: bytes) -> list[str]:
        self._buffer += self._decoder.decode(chunk)
        *lines, self._buffer = self._buffer.split("\n")
        return [line.rstrip("\r") for line in lines]

    def flush(self) -> list[str]:
        rest = self._buffer + self._decoder.decode(b"", final=True)
        self._buffer = ""
        return [rest.rstrip("\r")] if rest else []
