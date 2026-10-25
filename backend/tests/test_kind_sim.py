import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.jobs.context import JobContext, JobInputError
from app.jobs.diagnostics import parse_compile_log
from app.jobs.kinds import KINDS, sim
from app.jobs.runner import JobClass

FIXTURES = Path(__file__).parent / "fixtures" / "runs"


def params(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "top": "fifo",
        "sources": ["src/fifo.v"],
        "tests": ["test/test_fifo.py"],
        "simulator": "icarus",
        "defines": {"SIM": 1},
        "parameters": {"DEPTH": 8},
    }
    return base | overrides


def snapshot(run_dir: Path, *paths: str) -> None:
    for path in paths:
        target = run_dir / "project" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x\n", encoding="utf-8")


def test_sim_is_registered() -> None:
    assert KINDS["sim"] is sim
    assert sim.JOB_CLASS is JobClass.light
    # 1: a test failed or the code did not compile; 2 (bad spec) is a broken job.
    assert frozenset({0, 1}) == sim.OK_EXIT_CODES


class TestPrepare:
    def test_writes_the_spec_and_runs_the_tool(
        self, tmp_path: Path, job_context: JobContext
    ) -> None:
        snapshot(tmp_path, "src/fifo.v", "test/test_fifo.py")

        spec = sim.prepare(tmp_path, params(), job_context)

        assert json.loads((tmp_path / "sim.json").read_text(encoding="utf-8")) == params()
        assert spec.command == [
            "python",
            "/tools/grader/sim.py",
            "--spec",
            "/work/sim.json",
            "--project",
            "/work/project",
            "--workdir",
            "/work/build",
            "--out",
            "/work/result.json",
        ]
        assert spec.mount_tools is True
        assert spec.mount_content is False
        assert spec.job_class is JobClass.light

    @pytest.mark.parametrize("missing", ["src/fifo.v", "test/test_fifo.py"])
    def test_files_must_be_in_the_snapshot(
        self, tmp_path: Path, job_context: JobContext, missing: str
    ) -> None:
        snapshot(tmp_path, *[p for p in ("src/fifo.v", "test/test_fifo.py") if p != missing])
        with pytest.raises(JobInputError, match=missing):
            sim.prepare(tmp_path, params(), job_context)

    @pytest.mark.parametrize(
        "bad",
        [
            {"tests": []},
            {"tests": ["test/test-fifo.py"]},
            {"tests": ["test/fifo.v"]},
            {"simulator": "questa"},
            {"sources": ["../x.v"]},
            {"parameters": {"W": True}},
        ],
    )
    def test_rejects_bad_params(
        self, tmp_path: Path, job_context: JobContext, bad: dict[str, Any]
    ) -> None:
        snapshot(tmp_path, "src/fifo.v", "test/test_fifo.py")
        with pytest.raises(ValidationError):
            sim.prepare(tmp_path, params(**bad), job_context)


def copy_fixture(name: str, tmp_path: Path) -> Path:
    run_dir = tmp_path / "6c441c6559764865aca794a357acd304"
    shutil.copytree(FIXTURES / name, run_dir)
    return run_dir


class TestCollect:
    def test_icarus_pass_with_waveform(self, tmp_path: Path) -> None:
        run_dir = copy_fixture("sim-pass", tmp_path)

        result = sim.collect(run_dir)

        assert result["status"] == "pass"
        assert result["simulator"] == "icarus"
        assert result["simulator_version"].startswith("Icarus Verilog version")
        assert [(t["module"], t["passed"]) for t in result["tests"]] == [("test_fifo", True)] * 3
        assert result["wave_file"] == "build/sim_build/fifo.fst"
        assert result["wave_url"] == f"/api/runs/{run_dir.name}/files/build/sim_build/fifo.fst"
        assert result["diagnostics"] == []

    def test_verilator_waveform_lives_in_the_build_folder(self, tmp_path: Path) -> None:
        result = sim.collect(copy_fixture("sim-pass-verilator", tmp_path))

        assert result["status"] == "pass"
        assert result["simulator_version"].startswith("Verilator 5.053")
        assert result["wave_file"] == "build/dump.fst"

    def test_fail_keeps_the_testbench_messages(self, tmp_path: Path) -> None:
        result = sim.collect(copy_fixture("sim-fail", tmp_path))

        assert result["status"] == "fail"
        failed = {t["name"]: t["message"] for t in result["tests"] if not t["passed"]}
        assert failed["fills_to_depth_and_drains_in_order"] == "baca ke-2: dout = 3"

    def test_icarus_compile_error_points_at_project_files(self, tmp_path: Path) -> None:
        result = sim.collect(copy_fixture("sim-compile-icarus", tmp_path))

        assert result["status"] == "compile_error"
        assert result["wave_url"] is None
        assert [(d["file"], d["line"], d["col"], d["severity"]) for d in result["diagnostics"]] == [
            ("src/fifo.v", 21, None, "error"),
            ("src/fifo.v", 22, None, "error"),
        ]

    def test_verilator_compile_error_has_a_column(self, tmp_path: Path) -> None:
        result = sim.collect(copy_fixture("sim-compile-verilator", tmp_path))

        (diag,) = result["diagnostics"]  # "Exiting due to 1 error(s)" has no place
        assert (diag["file"], diag["line"], diag["col"]) == ("src/fifo.v", 22, 5)
        assert diag["message"].startswith("Verilator: syntax error")

    def test_missing_result_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            sim.collect(tmp_path)


def test_compile_log_ignores_files_outside_the_project() -> None:
    log = (
        "/work/build/sim_build/cocotb_iverilog_dump.v:3: error: nope\n"
        "/work/project/rtl/a.v:7: warning: Port 1 is too wide\n"
        "/work/project/rtl/a.v:7: warning: Port 1 is too wide\n"  # Icarus repeats itself
    )
    assert parse_compile_log(log, "/work/project") == [
        {
            "file": "rtl/a.v",
            "line": 7,
            "col": None,
            "end_col": None,
            "severity": "warning",
            "code": None,
            "message": "Port 1 is too wide",
        }
    ]
