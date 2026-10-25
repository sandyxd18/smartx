"""Simulate a project with its cocotb testbenches (tools/grader/sim.py in the image).

Like lint, the API copies the project into <run>/project/ and passes the resolved
smartx.yaml as params. prepare() writes those params as the tool's spec (sim.json).
"""

import json
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.jobs.artifacts import file_url, run_relative
from app.jobs.context import JobContext, JobInputError
from app.jobs.diagnostics import ProjectDiagnostic, parse_compile_log
from app.jobs.kinds.lint import PROJECT_DIR, ProjectPath
from app.jobs.runner import ContainerSpec, JobClass
from app.projects.config import Name, Scalar, check_test_file

JOB_CLASS = JobClass.light
# sim.py: 0 = all tests passed, 1 = a test failed or the code did not compile.
OK_EXIT_CODES = frozenset({0, 1})

SPEC_FILE = "sim.json"
WORK_DIR = "build"
RESULT_FILE = "result.json"

TestFile = Annotated[str, AfterValidator(check_test_file)]


class Params(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top: Name
    sources: Annotated[list[ProjectPath], Field(min_length=1)]
    tests: Annotated[list[TestFile], Field(min_length=1)]
    simulator: Literal["icarus", "verilator"]
    defines: dict[Name, Scalar] = {}
    parameters: dict[Name, Scalar] = {}


class SimTest(BaseModel):
    module: str = ""  # the testbench module (file stem)
    name: str
    passed: bool
    message: str = ""
    sim_time_ns: float = 0


class SimResult(BaseModel):
    """Run.result of a sim run."""

    status: Literal["pass", "fail", "compile_error", "error"]
    top: str
    simulator: str
    simulator_version: str = ""
    tests: list[SimTest] = []
    # Compiler messages about project files (only for compile_error).
    diagnostics: list[ProjectDiagnostic] = []
    log: str = ""
    wave_file: str | None = None  # relative to the run folder
    wave_url: str | None = None


def prepare(run_dir: Path, params: dict[str, Any], ctx: JobContext) -> ContainerSpec:
    p = Params.model_validate(params)
    for path in [*p.sources, *p.tests]:
        if not (run_dir / PROJECT_DIR / path).is_file():
            raise JobInputError(f"File '{path}' tidak ada di salinan proyek.")
    (run_dir / SPEC_FILE).write_text(
        json.dumps(p.model_dump(), indent=2), encoding="utf-8", newline="\n"
    )
    return ContainerSpec(
        command=[
            "python",
            "/tools/grader/sim.py",
            "--spec",
            f"/work/{SPEC_FILE}",
            "--project",
            f"/work/{PROJECT_DIR}",
            "--workdir",
            f"/work/{WORK_DIR}",
            "--out",
            f"/work/{RESULT_FILE}",
        ],
        job_class=JOB_CLASS,
        mount_tools=True,
    )


def collect(run_dir: Path) -> dict[str, Any]:
    data = json.loads((run_dir / RESULT_FILE).read_text(encoding="utf-8"))
    status = data["status"]
    log = data.get("log") or ""
    wave = run_relative(data.get("wave_file"), run_dir)
    result = SimResult.model_validate(
        {
            "status": status,
            "top": data["top"],
            "simulator": data["simulator"],
            "simulator_version": data.get("simulator_version") or "",
            "tests": data.get("tests", []),
            "diagnostics": parse_compile_log(log, f"/work/{PROJECT_DIR}")
            if status == "compile_error"
            else [],
            "log": log,
            "wave_file": wave,
            "wave_url": file_url(run_dir, wave),
        }
    )
    return result.model_dump()
