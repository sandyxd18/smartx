import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.jobs.context import JobContext, JobInputError
from app.jobs.kinds import KINDS, fpga
from app.jobs.runner import JobClass

FIXTURES = Path(__file__).parent / "fixtures" / "runs"


def params(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "top": "blinky",
        "sources": ["src/blinky.v"],
        "board": "tang-nano-9k",
        "constraints": "constraints/tang-nano-9k.cst",
        "freq_mhz": 27,
    }
    return base | overrides


def snapshot(run_dir: Path, *paths: str) -> None:
    for path in paths:
        target = run_dir / "project" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x\n", encoding="utf-8")


def fixture_run(tmp_path: Path, name: str) -> Path:
    run_dir = tmp_path / "abc123"  # collect() builds URLs from the folder name
    shutil.copytree(FIXTURES / name, run_dir)
    return run_dir


def test_fpga_is_registered() -> None:
    assert KINDS["fpga"] is fpga
    assert fpga.JOB_CLASS is JobClass.light
    # 1: a stage failed (a result); 2 (bad spec) is a broken job.
    assert frozenset({0, 1}) == fpga.OK_EXIT_CODES


class TestPrepare:
    def test_writes_one_command_per_stage(self, tmp_path: Path, job_context: JobContext) -> None:
        snapshot(tmp_path, "src/blinky.v", "constraints/tang-nano-9k.cst")

        spec = fpga.prepare(tmp_path, params(), job_context)

        assert spec.command == [
            "python",
            "/tools/fpga/build.py",
            "--spec",
            "/work/fpga.json",
            "--workdir",
            "/work/build",
            "--out",
            "/work/result.json",
        ]
        assert spec.mount_tools is True
        assert spec.mount_content is False  # user code never sees content/
        written = json.loads((tmp_path / "fpga.json").read_text(encoding="utf-8"))
        stages = {s["id"]: s["command"] for s in written["stages"]}
        assert list(stages) == ["synth", "pnr", "pack"]
        assert stages["synth"] == ["yosys", "-q", "-l", "yosys.log", "-s", "synth.ys"]
        pnr = stages["pnr"]
        assert pnr[:3] == ["nextpnr-himbaechel", "--json", "netlist.json"]
        assert "cst=/work/project/constraints/tang-nano-9k.cst" in pnr
        assert pnr[pnr.index("--freq") + 1] == "27"
        assert pnr[-2:] == ["-q", "--timing-allow-fail"]
        assert stages["pack"] == ["gowin_pack", "-d", "GW1N-9C", "-o", "bitstream.fs", "pnr.json"]
        assert written["bitstream_file"] == "bitstream.fs"

    def test_synth_script(self, tmp_path: Path, job_context: JobContext) -> None:
        snapshot(tmp_path, "src/blinky.v", "src/sub/util.sv", "constraints/tang-nano-9k.cst")
        p = params(
            sources=["src/blinky.v", "src/sub/util.sv"],
            defines={"SIM": 1},
            parameters={"W": 6, "INIT": "8'hFF"},
        )

        fpga.prepare(tmp_path, p, job_context)

        flags = "-I/work/project/src -I/work/project/src/sub -DSIM=1"
        assert (tmp_path / "build" / "synth.ys").read_text(encoding="utf-8") == (
            f"read_verilog {flags} /work/project/src/blinky.v\n"
            f"read_verilog -sv {flags} /work/project/src/sub/util.sv\n"
            "chparam -set W 6 -set INIT 8'hFF blinky\n"
            "synth_gowin -top blinky -json netlist.json\n"
            "tee -q -o stat.txt stat\n"
            "tee -q -o stat.json stat -json\n"
        )

    @pytest.mark.parametrize("missing", ["src/blinky.v", "constraints/tang-nano-9k.cst"])
    def test_files_must_be_in_the_snapshot(
        self, tmp_path: Path, job_context: JobContext, missing: str
    ) -> None:
        present = {"src/blinky.v", "constraints/tang-nano-9k.cst"} - {missing}
        snapshot(tmp_path, *present)
        with pytest.raises(JobInputError, match=missing):
            fpga.prepare(tmp_path, params(), job_context)

    def test_unknown_board(self, tmp_path: Path, job_context: JobContext) -> None:
        snapshot(tmp_path, "src/blinky.v", "constraints/tang-nano-9k.cst")
        with pytest.raises(JobInputError, match="Board 'papan-x' tidak dikenal"):
            fpga.prepare(tmp_path, params(board="papan-x"), job_context)

    @pytest.mark.parametrize(
        "change",
        [{"defines": {"MSG": "a b"}}, {"parameters": {"S": '"teks"'}}, {"defines": {"X": "1;"}}],
    )
    def test_values_must_be_one_script_token(
        self, tmp_path: Path, job_context: JobContext, change: dict[str, Any]
    ) -> None:
        snapshot(tmp_path, "src/blinky.v", "constraints/tang-nano-9k.cst")
        with pytest.raises(JobInputError, match="tidak bisa dipakai untuk sintesis"):
            fpga.prepare(tmp_path, params(**change), job_context)

    @pytest.mark.parametrize(
        "change",
        [
            {"constraints": "../luar.cst"},
            {"sources": []},
            {"freq_mhz": 0},
            {"top": "1abc"},
            {"extra": 1},
        ],
    )
    def test_params_are_validated(
        self, tmp_path: Path, job_context: JobContext, change: dict[str, Any]
    ) -> None:
        with pytest.raises(ValidationError):
            fpga.prepare(tmp_path, params(**change), job_context)


class TestCollect:
    def test_success_links_the_outputs(self, tmp_path: Path) -> None:
        result = fpga.collect(fixture_run(tmp_path, "fpga-ok"))

        assert result["status"] == "ok"
        assert (result["board"], result["top"], result["freq_mhz"]) == (
            "tang-nano-9k",
            "blinky",
            27,
        )
        assert [(s["id"], s["status"]) for s in result["stages"]] == [
            ("synth", "ok"),
            ("pnr", "ok"),
            ("pack", "ok"),
        ]
        assert result["stages"][2]["seconds"] == 3.2
        logs = [s["log_url"] for s in result["stages"]]
        assert logs == [
            "/api/runs/abc123/files/build/yosys.log",
            "/api/runs/abc123/files/build/nextpnr.log",
            None,
        ]
        assert result["bitstream_url"] == "/api/runs/abc123/files/build/bitstream.fs"
        assert result["report_url"] == "/api/runs/abc123/files/build/report.json"
        assert result["stat_url"] == "/api/runs/abc123/files/build/stat.txt"
        assert result["error"] is None and result["diagnostics"] == []
        assert result["versions"]["yosys"].startswith("Yosys 0.70")

    def test_synthesis_error_points_at_the_line(self, tmp_path: Path) -> None:
        result = fpga.collect(fixture_run(tmp_path, "fpga-synth-error"))

        assert result["status"] == "failed"
        assert [s["status"] for s in result["stages"]] == ["failed", "skipped", "skipped"]
        [diag] = result["diagnostics"]
        assert (diag["file"], diag["line"], diag["severity"]) == ("src/blinky.v", 7, "error")
        assert diag["message"].startswith("syntax error, unexpected TOK_REG")
        assert result["error"].startswith("syntax error")
        assert result["bitstream_url"] is None and result["report_url"] is None

    def test_place_and_route_error(self, tmp_path: Path) -> None:
        result = fpga.collect(fixture_run(tmp_path, "fpga-pnr-error"))

        assert [s["status"] for s in result["stages"]] == ["ok", "failed", "skipped"]
        assert result["error"] == "Unconstrained IO:led_OBUF_O"
        assert result["diagnostics"] == []
        assert result["stat_url"] is not None  # synthesis finished
        assert result["bitstream_url"] is None

    def test_pack_error_is_read_from_the_run_log(self, tmp_path: Path) -> None:
        run_dir = fixture_run(tmp_path, "fpga-ok")
        data = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        data["status"] = "failed"
        data["stages"][2].update(status="failed", exit_code=1)
        (run_dir / "result.json").write_text(json.dumps(data), encoding="utf-8")
        (run_dir / "run.log").write_text("==> Pack\nERROR: bad netlist\n", encoding="utf-8")

        result = fpga.collect(run_dir)

        assert result["error"] == "bad netlist"
        assert result["bitstream_url"] is None
