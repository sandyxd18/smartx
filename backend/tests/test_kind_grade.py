import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlmodel import Session

from app.db import init_db, make_engine
from app.jobs.context import JobContext, JobInputError
from app.jobs.events import EventHub
from app.jobs.fake_runner import FakeJob, FakeRunner
from app.jobs.kinds import KINDS, grade
from app.jobs.queue import JobQueue
from app.jobs.runner import JobClass
from app.models import Run, RunStatus

FIXTURES = Path(__file__).parent / "fixtures" / "runs"
CODE = "module counter4(input clk, input rst, input en, output reg [3:0] q);\nendmodule\n"


def test_grade_is_registered() -> None:
    assert KINDS["grade"] is grade
    assert grade.JOB_CLASS is JobClass.light
    # The grader exits 1 when tests fail: that is a result, not a broken job.
    assert frozenset({0, 1}) == grade.OK_EXIT_CODES


class TestPrepare:
    def test_stages_test_files_and_user_code(self, tmp_path: Path, job_context: JobContext) -> None:
        spec = grade.prepare(tmp_path, {"exercise_id": "counter-4bit", "code": CODE}, job_context)

        assert sorted(p.name for p in (tmp_path / "exercise").iterdir()) == [
            "exercise.yaml",
            "test_counter4.py",
        ]
        assert (tmp_path / "user.v").read_bytes() == CODE.encode()
        assert spec.command == [
            "python",
            "/tools/grader/grade.py",
            "--exercise",
            "/exercise",
            "--source",
            "/work/user.v",
            "--workdir",
            "/work/build",
            "--out",
            "/work/result.json",
            "--simulator",
            "icarus",
        ]
        assert spec.job_class is JobClass.light
        assert spec.mount_tools is True
        assert spec.readonly_subdirs == {"exercise": "/exercise"}
        assert spec.timeout_s == 30 + grade.OVERHEAD_S  # counter-4bit has timeout_s: 30

    def test_never_exposes_the_solution(self, tmp_path: Path, job_context: JobContext) -> None:
        spec = grade.prepare(tmp_path, {"exercise_id": "counter-4bit", "code": CODE}, job_context)

        solution = (job_context.catalog.get("counter-4bit").solution_path).read_bytes()  # type: ignore[union-attr]
        assert spec.mount_content is False
        for path in tmp_path.rglob("*"):
            assert not path.name.startswith("solution")
            if path.is_file():
                assert path.read_bytes() != solution

    def test_unknown_exercise(self, tmp_path: Path, job_context: JobContext) -> None:
        with pytest.raises(JobInputError, match="tidak-ada"):
            grade.prepare(tmp_path, {"exercise_id": "tidak-ada", "code": CODE}, job_context)

    @pytest.mark.parametrize(
        "params",
        [
            {"exercise_id": "../counter-4bit", "code": CODE},
            {"exercise_id": "counter-4bit"},
            {"exercise_id": "counter-4bit", "code": 42},
            {"exercise_id": "counter-4bit", "code": "x" * (grade.MAX_CODE_CHARS + 1)},
            {"exercise_id": "counter-4bit", "code": CODE, "simulator": "verilator"},
        ],
    )
    def test_rejects_bad_params(
        self, tmp_path: Path, job_context: JobContext, params: dict[str, object]
    ) -> None:
        with pytest.raises(ValidationError):
            grade.prepare(tmp_path, params, job_context)


def copy_fixture(
    name: str, tmp_path: Path, run_id: str = "3d2b1bde0c1946ed91b904bf4e735ed3"
) -> Path:
    run_dir = tmp_path / run_id
    shutil.copytree(FIXTURES / name, run_dir)
    return run_dir


class TestCollect:
    def test_pass(self, tmp_path: Path) -> None:
        run_dir = copy_fixture("grade-pass", tmp_path)

        result = grade.collect(run_dir)

        assert result["status"] == "pass"
        assert result["exercise_id"] == "counter-4bit"
        assert [t["name"] for t in result["tests"]] == [
            "reset_sets_zero",
            "counts_and_wraps",
            "random_stimulus",
        ]
        assert all(t["passed"] for t in result["tests"])
        assert result["diagnostics"] == []
        assert result["wave_file"] == "build/sim_build/counter4.fst"
        assert result["wave_url"] == (
            f"/api/runs/{run_dir.name}/files/build/sim_build/counter4.fst"
        )

    def test_fail_keeps_messages(self, tmp_path: Path) -> None:
        result = grade.collect(copy_fixture("grade-fail", tmp_path))

        assert result["status"] == "fail"
        assert not any(t["passed"] for t in result["tests"])
        assert "XXXX" in result["tests"][0]["message"]
        assert result["wave_url"] is not None

    def test_lint_findings_from_verilator(self, tmp_path: Path) -> None:
        result = grade.collect(copy_fixture("grade-fail", tmp_path))

        # The starter's ports are unused and q is never driven.
        assert [(d["line"], d["code"]) for d in result["lint"]] == [
            (2, "UNUSEDSIGNAL"),
            (3, "UNUSEDSIGNAL"),
            (4, "UNUSEDSIGNAL"),
            (5, "UNDRIVEN"),
        ]
        assert all(d["severity"] == "warning" for d in result["lint"])
        assert result["diagnostics"] == []

    def test_old_results_without_lint(self, tmp_path: Path) -> None:
        assert grade.collect(copy_fixture("grade-pass", tmp_path))["lint"] == []

    def test_compile_error_lists_lines_of_user_code_only(self, tmp_path: Path) -> None:
        result = grade.collect(copy_fixture("grade-compile-error", tmp_path))

        assert result["status"] == "compile_error"
        assert result["tests"] == []
        assert result["wave_file"] is None and result["wave_url"] is None
        # cocotb's own cocotb_iverilog_dump.v errors are not the user's lines.
        assert [(d["line"], d["severity"], d["message"]) for d in result["diagnostics"]] == [
            (4, "error", "syntax error"),
            (5, "error", "Syntax in assignment statement l-value."),
            (6, "error", "syntax error"),
        ]
        # Icarus already marks these lines; Verilator would only repeat them.
        assert result["lint"] == []

    @pytest.mark.parametrize(
        "wave_file",
        ["/etc/passwd", "/work/../etc/passwd", "/work/build/missing.fst", "relative.fst", 7],
    )
    def test_ignores_unusable_wave_paths(self, tmp_path: Path, wave_file: object) -> None:
        run_dir = copy_fixture("grade-pass", tmp_path)
        data = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        data["wave_file"] = wave_file
        (run_dir / "result.json").write_text(json.dumps(data), encoding="utf-8")

        result = grade.collect(run_dir)

        assert result["wave_file"] is None
        assert result["wave_url"] is None

    def test_missing_result_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            grade.collect(tmp_path)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (
            "/work/build/dut.v:3: error: Unknown module type: foo",
            (3, "error", "Unknown module type: foo"),
        ),
        (
            "/work/build/dut.v:12: warning: Port 2 (b) of x expects 4 bits",
            (12, "warning", "Port 2 (b) of x expects 4 bits"),
        ),
        ("dut.v:1: syntax error", (1, "error", "syntax error")),
    ],
)
def test_parse_diagnostics(line: str, expected: tuple[int, str, str]) -> None:
    diag = grade.parse_diagnostics(f"noise\n{line}\n/work/build/sim_build/x.v:1: error: no\n")
    assert diag == [{"line": expected[0], "severity": expected[1], "message": expected[2]}]


async def test_failing_tests_still_make_a_succeeded_run(
    tmp_path: Path, job_context: JobContext
) -> None:
    settings = job_context.settings
    engine = make_engine("sqlite://")
    init_db(engine)
    runner = FakeRunner(FakeJob(exit_code=1, fixture_dir=FIXTURES / "grade-fail"))
    queue = JobQueue(
        runner=runner, settings=settings, engine=engine, events=EventHub(), context=job_context
    )
    with Session(engine) as s:
        run = Run(kind="grade", params={"exercise_id": "counter-4bit", "code": CODE})
        s.add(run)
        s.commit()
        run_id = run.id

    await queue.submit(run_id)

    with Session(engine) as s:
        done = s.get(Run, run_id)
        assert done is not None
        assert done.status == RunStatus.succeeded
        assert done.exit_code == 1
        assert done.result is not None and done.result["status"] == "fail"
    spec = runner.started[0][1]
    assert spec.timeout_s == 30 + grade.OVERHEAD_S
    engine.dispose()
