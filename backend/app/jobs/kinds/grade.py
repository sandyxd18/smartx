"""Grade a user's Verilog against an exercise testbench with tools/grader/grade.py.

Only exercise.yaml and the testbench are copied into the run folder (mounted read-only
at /exercise). content/ is not mounted, so user code cannot read solution.v.
"""

import json
import re
import shutil
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.content.models import ExerciseId
from app.jobs.context import JobContext, JobInputError
from app.jobs.runner import ContainerSpec, JobClass

JOB_CLASS = JobClass.light
# grade.py: 0 = all tests passed, 1 = a test failed or the code did not compile.
OK_EXIT_CODES = frozenset({0, 1})

MAX_CODE_CHARS = 200_000
# Added to the exercise's timeout_s for container start, compilation and cocotb startup.
OVERHEAD_S = 30

EXERCISE_DIR = "exercise"
SOURCE_FILE = "user.v"
WORK_DIR = "build"
RESULT_FILE = "result.json"

# Icarus: "<path>/dut.v:<line>: [error: |warning: ]<message>". The grader copies the
# user's code to dut.v; other files (cocotb's dump module) are not the user's.
_DIAGNOSTIC = re.compile(r"^(?:\S*/)?dut\.v:(\d+):\s*(?:(error|warning):\s*)?(.*)$")


class Params(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    exercise_id: ExerciseId
    code: str = Field(max_length=MAX_CODE_CHARS)


def prepare(run_dir: Path, params: dict[str, Any], ctx: JobContext) -> ContainerSpec:
    p = Params.model_validate(params)
    exercise = ctx.catalog.get(p.exercise_id)
    if exercise is None:
        raise JobInputError(f"Soal '{p.exercise_id}' tidak ditemukan.")

    staged = run_dir / EXERCISE_DIR
    staged.mkdir(exist_ok=True)
    shutil.copyfile(exercise.dir / "exercise.yaml", staged / "exercise.yaml")
    shutil.copyfile(exercise.test_path, staged / exercise.test_path.name)
    (run_dir / SOURCE_FILE).write_text(p.code, encoding="utf-8", newline="\n")

    return ContainerSpec(
        command=[
            "python",
            "/tools/grader/grade.py",
            "--exercise",
            f"/{EXERCISE_DIR}",
            "--source",
            f"/work/{SOURCE_FILE}",
            "--workdir",
            f"/work/{WORK_DIR}",
            "--out",
            f"/work/{RESULT_FILE}",
            "--simulator",
            "icarus",
        ],
        job_class=JOB_CLASS,
        mount_tools=True,
        readonly_subdirs={EXERCISE_DIR: f"/{EXERCISE_DIR}"},
        timeout_s=exercise.meta.timeout_s + OVERHEAD_S,
    )


def parse_diagnostics(log: str) -> list[dict[str, Any]]:
    """Compiler messages about the user's code, with line numbers for the editor."""
    diagnostics = []
    for raw in log.splitlines():
        match = _DIAGNOSTIC.match(raw.strip())
        if match:
            line, severity, message = match.groups()
            diagnostics.append(
                {"line": int(line), "severity": severity or "error", "message": message.strip()}
            )
    return diagnostics


def _run_relative(container_path: object, run_dir: Path) -> str | None:
    """Map /work/... (as the grader saw it) to a path relative to the run folder."""
    if not isinstance(container_path, str):
        return None
    path = PurePosixPath(container_path)
    if not path.is_relative_to("/work") or ".." in path.parts:
        return None
    rel = path.relative_to("/work")
    return rel.as_posix() if (run_dir / rel).is_file() else None


def collect(run_dir: Path) -> dict[str, Any]:
    data = json.loads((run_dir / RESULT_FILE).read_text(encoding="utf-8"))
    status = data["status"]
    log = data.get("log") or ""
    wave = _run_relative(data.get("wave_file"), run_dir)
    return {
        "exercise_id": data["exercise"],
        "status": status,  # pass | fail | compile_error | error
        "simulator": data.get("simulator"),
        "tests": data.get("tests", []),
        "diagnostics": parse_diagnostics(log) if status == "compile_error" else [],
        "log": log,
        "wave_file": wave,
        "wave_url": f"/api/runs/{run_dir.name}/files/{wave}" if wave else None,
    }
