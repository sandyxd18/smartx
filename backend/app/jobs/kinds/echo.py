"""Smoke-test job: print the Yosys version. Proves the container pipeline works."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.jobs.context import JobContext
from app.jobs.runner import ContainerSpec, JobClass

JOB_CLASS = JobClass.light
OK_EXIT_CODES = frozenset({0})


class Params(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    # Keep the container alive afterwards; used to exercise cancel and timeout.
    sleep_s: int = Field(default=0, ge=0, le=600)


def prepare(run_dir: Path, params: dict[str, Any], ctx: JobContext) -> ContainerSpec:
    p = Params.model_validate(params)
    if p.sleep_s:
        # sleep_s is a validated int, so building a shell string is safe here.
        command = ["sh", "-c", f"yosys -V && sleep {p.sleep_s}"]
        return ContainerSpec(command=command, job_class=JOB_CLASS)
    return ContainerSpec(command=["yosys", "-V"], job_class=JOB_CLASS)


def collect(run_dir: Path) -> dict[str, Any]:
    log = run_dir / "run.log"
    lines = log.read_text(encoding="utf-8").splitlines() if log.is_file() else []
    version = next((line for line in lines if line.startswith("Yosys ")), None)
    return {"yosys_version": version}
