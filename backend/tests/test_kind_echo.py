from pathlib import Path

import pytest
from pydantic import ValidationError

from app.jobs.context import JobContext
from app.jobs.kinds import KINDS, echo
from app.jobs.runner import JobClass

FIXTURES = Path(__file__).parent / "fixtures" / "runs"


def test_echo_is_registered() -> None:
    assert KINDS["echo"] is echo
    assert echo.JOB_CLASS is JobClass.light


def test_prepare_runs_yosys_version(tmp_path: Path, job_context: JobContext) -> None:
    spec = echo.prepare(tmp_path, {}, job_context)
    assert spec.command == ["yosys", "-V"]
    assert spec.job_class is JobClass.light
    assert not spec.mount_content  # echo needs nothing from content/


def test_prepare_with_sleep(tmp_path: Path, job_context: JobContext) -> None:
    spec = echo.prepare(tmp_path, {"sleep_s": 60}, job_context)
    assert spec.command == ["sh", "-c", "yosys -V && sleep 60"]


@pytest.mark.parametrize("bad", [-1, 601, "1; rm -rf /", 1.5])
def test_prepare_rejects_bad_sleep(tmp_path: Path, bad: object, job_context: JobContext) -> None:
    with pytest.raises(ValidationError):
        echo.prepare(tmp_path, {"sleep_s": bad}, job_context)


def test_prepare_rejects_unknown_params(tmp_path: Path, job_context: JobContext) -> None:
    with pytest.raises(ValidationError):
        echo.prepare(tmp_path, {"command": "ls"}, job_context)


def test_collect_reads_yosys_version() -> None:
    version = echo.collect(FIXTURES / "echo")["yosys_version"]
    assert version == (
        "Yosys 0.70+219 (git sha1 5053d0e26, Release, Clang /usr/bin/clang++ 21.1.8)"
    )


def test_collect_without_log(tmp_path: Path) -> None:
    assert echo.collect(tmp_path) == {"yosys_version": None}
