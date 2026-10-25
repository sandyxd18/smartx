"""Lint a project's sources with `verilator --lint-only -Wall`.

The API copies every project file to <run>/project/ before submitting (a snapshot of
what the user saw when clicking Lint) and puts the resolved config in the params.
Verilator writes its findings as SARIF, which collect() turns into diagnostics.
"""

import json
from pathlib import Path, PurePosixPath
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.jobs.context import JobContext, JobInputError
from app.jobs.diagnostics import ProjectDiagnostic
from app.jobs.runner import ContainerSpec, JobClass
from app.jobs.verilator_lint import parse_sarif
from app.projects.config import Name, Scalar
from app.projects.paths import normalize_project_path

JOB_CLASS = JobClass.light
# Verilator exits 1 when it reports errors (syntax, missing modules): still a result.
OK_EXIT_CODES = frozenset({0, 1})

PROJECT_DIR = "project"  # the snapshot, relative to the run folder (= /work)
SARIF_FILE = "lint.sarif"

ProjectPath = Annotated[str, AfterValidator(normalize_project_path)]


class Params(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top: Name
    sources: Annotated[list[ProjectPath], Field(min_length=1)]  # files, already matched
    defines: dict[Name, Scalar] = {}
    parameters: dict[Name, Scalar] = {}


class LintResult(BaseModel):
    """Run.result of a lint run."""

    errors: int
    warnings: int
    diagnostics: list[ProjectDiagnostic]


def prepare(run_dir: Path, params: dict[str, Any], ctx: JobContext) -> ContainerSpec:
    p = Params.model_validate(params)
    for source in p.sources:
        if not (run_dir / PROJECT_DIR / source).is_file():
            raise JobInputError(f"File sumber '{source}' tidak ada di salinan proyek.")

    sources = [f"{PROJECT_DIR}/{s}" for s in p.sources]
    # Every source folder is an include folder, so `include "defs.vh" works next to it.
    folders = list(dict.fromkeys(str(PurePosixPath(s).parent) for s in sources))
    return ContainerSpec(
        command=[
            "verilator",
            "--lint-only",
            "-Wall",
            # The editor may save without a final newline; not worth a warning.
            "-Wno-EOFNEWLINE",
            # Warnings must not stop the run: they are the result.
            "-Wno-fatal",
            "--quiet",
            "--diagnostics-sarif",
            "--diagnostics-sarif-output",
            SARIF_FILE,
            "--top-module",
            p.top,
            *[f"-I{folder}" for folder in folders],
            *[f"-D{name}={value}" for name, value in p.defines.items()],
            *[f"-G{name}={value}" for name, value in p.parameters.items()],
            *sources,
        ],
        job_class=JOB_CLASS,
    )


def collect(run_dir: Path) -> dict[str, Any]:
    data = json.loads((run_dir / SARIF_FILE).read_text(encoding="utf-8"))
    diagnostics = parse_sarif(data, f"/work/{PROJECT_DIR}")
    result = LintResult(
        errors=sum(d["severity"] == "error" for d in diagnostics),
        warnings=sum(d["severity"] == "warning" for d in diagnostics),
        diagnostics=[ProjectDiagnostic.model_validate(d) for d in diagnostics],
    )
    return result.model_dump()
