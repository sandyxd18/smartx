import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.jobs.context import JobContext, JobInputError
from app.jobs.kinds import KINDS, lint
from app.jobs.runner import JobClass

FIXTURES = Path(__file__).parent / "fixtures" / "runs"


def params(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "top": "top",
        "sources": ["src/top.v", "src/sub/helper.v"],
        "defines": {},
        "parameters": {},
    }
    return base | overrides


def snapshot(run_dir: Path, *paths: str) -> None:
    for path in paths:
        target = run_dir / "project" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("module x; endmodule\n", encoding="utf-8")


def test_lint_is_registered() -> None:
    assert KINDS["lint"] is lint
    assert lint.JOB_CLASS is JobClass.light
    # 1: Verilator found errors (e.g. syntax); that is a result, not a broken job.
    assert frozenset({0, 1}) == lint.OK_EXIT_CODES


class TestPrepare:
    def test_command(self, tmp_path: Path, job_context: JobContext) -> None:
        snapshot(tmp_path, "src/top.v", "src/sub/helper.v")

        spec = lint.prepare(
            tmp_path,
            params(defines={"SIM": 1}, parameters={"WIDTH": 8, "INIT": "8'hFF"}),
            job_context,
        )

        assert spec.command == [
            "verilator",
            "--lint-only",
            "-Wall",
            "-Wno-EOFNEWLINE",
            "-Wno-fatal",
            "--quiet",
            "--diagnostics-sarif",
            "--diagnostics-sarif-output",
            "lint.sarif",
            "--top-module",
            "top",
            "-Iproject/src",
            "-Iproject/src/sub",
            "-DSIM=1",
            "-GWIDTH=8",
            "-GINIT=8'hFF",
            "project/src/top.v",
            "project/src/sub/helper.v",
        ]
        assert spec.job_class is JobClass.light
        assert spec.mount_content is False
        assert spec.mount_tools is False

    def test_source_missing_from_snapshot(self, tmp_path: Path, job_context: JobContext) -> None:
        snapshot(tmp_path, "src/top.v")
        with pytest.raises(JobInputError, match="src/sub/helper.v"):
            lint.prepare(tmp_path, params(), job_context)

    @pytest.mark.parametrize(
        "bad",
        [
            {"top": "9top"},
            {"sources": []},
            {"sources": ["../etc/passwd"]},
            {"sources": ["/abs.v"]},
            {"defines": {"A B": 1}},
            {"defines": {"SIM": True}},
            {"parameters": {"W": None}},
            {"extra": 1},
        ],
    )
    def test_rejects_bad_params(
        self, tmp_path: Path, job_context: JobContext, bad: dict[str, Any]
    ) -> None:
        snapshot(tmp_path, "src/top.v", "src/sub/helper.v")
        with pytest.raises(ValidationError):
            lint.prepare(tmp_path, params(**bad), job_context)


def copy_fixture(name: str, tmp_path: Path) -> Path:
    run_dir = tmp_path / "run"
    shutil.copytree(FIXTURES / name, run_dir)
    return run_dir


class TestCollect:
    def test_warnings_across_files(self, tmp_path: Path) -> None:
        result = lint.collect(copy_fixture("lint-warnings", tmp_path))

        assert result["errors"] == 0
        assert result["warnings"] == 3
        found = [
            (d["file"], d["line"], d["col"], d["end_col"], d["code"]) for d in result["diagnostics"]
        ]
        # Sorted by file, then position.
        assert found == [
            ("src/sub/helper.v", 1, 33, 34, "UNUSEDSIGNAL"),
            ("src/sub/helper.v", 2, 17, 18, "WIDTHTRUNC"),
            ("src/top.v", 1, 24, 27, "UNUSEDSIGNAL"),
        ]
        width = result["diagnostics"][1]
        assert width["severity"] == "warning"
        assert width["message"].startswith("Lebar bit berbeda")
        assert "generates 4 bits" in width["message"]
        assert "\n" not in width["message"]

    def test_syntax_error(self, tmp_path: Path) -> None:
        result = lint.collect(copy_fixture("lint-error", tmp_path))

        assert result["errors"] == 1 and result["warnings"] == 0
        (diag,) = result["diagnostics"]  # "Cannot continue" has no location
        assert diag["file"] == "src/broken.v"
        assert (diag["line"], diag["col"], diag["severity"]) == (3, 1, "error")
        assert diag["code"] is None
        assert diag["message"].startswith("Verilator: syntax error")

    def test_ignores_files_outside_the_project(self, tmp_path: Path) -> None:
        run_dir = copy_fixture("lint-warnings", tmp_path)
        data = json.loads((run_dir / "lint.sarif").read_text(encoding="utf-8"))
        loc = data["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
        loc["artifactLocation"]["uri"] = "file:///usr/share/verilator/include/verilated_std.sv"
        (run_dir / "lint.sarif").write_text(json.dumps(data), encoding="utf-8")

        result = lint.collect(run_dir)

        assert result["warnings"] == 2
        assert all(d["file"].startswith("src/") for d in result["diagnostics"])

    def test_missing_sarif_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            lint.collect(tmp_path)
