"""Job kinds. Each kind is a module with JOB_CLASS, prepare() and collect()."""

from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel

from app.jobs.kinds import echo
from app.jobs.runner import ContainerSpec, JobClass


class JobKind(Protocol):
    JOB_CLASS: JobClass
    # Validates the user-supplied params; prepare() receives the validated dict.
    Params: type[BaseModel]

    def prepare(self, run_dir: Path, params: dict[str, Any]) -> ContainerSpec: ...

    def collect(self, run_dir: Path) -> dict[str, Any]: ...


KINDS: dict[str, JobKind] = {
    "echo": echo,
}
