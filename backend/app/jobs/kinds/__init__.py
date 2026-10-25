"""Job kinds. Each kind is a module with the attributes of JobKind."""

from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel

from app.jobs.context import JobContext
from app.jobs.kinds import echo, grade, lint
from app.jobs.runner import ContainerSpec, JobClass


class JobKind(Protocol):
    JOB_CLASS: JobClass
    # Container exit codes that mean "the job did its work" (collect() decides the verdict).
    OK_EXIT_CODES: frozenset[int]
    # Validates the user-supplied params; prepare() receives the validated dict.
    Params: type[BaseModel]

    def prepare(self, run_dir: Path, params: dict[str, Any], ctx: JobContext) -> ContainerSpec:
        """Write inputs into run_dir and describe the container. May raise JobInputError."""
        ...

    def collect(self, run_dir: Path) -> dict[str, Any]:
        """Read the outputs left in run_dir after the container exited."""
        ...


KINDS: dict[str, JobKind] = {
    "echo": echo,
    "grade": grade,
    "lint": lint,
}
