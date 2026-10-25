"""tools/grader/grade.py runs inside the toolchain image; its pure helpers are tested here."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from app.config import REPO_ROOT


def load_grader() -> ModuleType:
    spec = importlib.util.spec_from_file_location("grade", REPO_ROOT / "tools/grader/grade.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("raw", "shown"),
    [
        # cocotb appends assertion introspection after the author's message.
        (
            "Siklus 7: clean = 1, seharusnya 0\nassert 1 == 0\n +  where 0 = <test>",
            "Siklus 7: clean = 1, seharusnya 0",
        ),
        ("q bernilai X (X/Z). Biasanya karena ...", "q bernilai X (X/Z). Biasanya karena ..."),
        # A bare assert has nothing better to show.
        ("assert 1 == 0", "assert 1 == 0"),
        ("  baris satu\nbaris dua  ", "baris satu\nbaris dua"),
    ],
)
def test_clean_message(raw: str, shown: str) -> None:
    assert load_grader().clean_message(raw) == shown


def test_lint_command_checks_the_user_file_against_the_toplevel() -> None:
    cmd = load_grader().lint_command("counter4")

    assert cmd[0] == "verilator"
    assert {"--lint-only", "-Wall", "-Wno-fatal"} <= set(cmd)
    # dut.v never matches the module name; that warning would only be noise.
    assert "-Wno-DECLFILENAME" in cmd
    assert cmd[cmd.index("--top-module") + 1] == "counter4"
    assert cmd[-1] == "dut.v"


def test_lint_never_breaks_grading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    grader = load_grader()
    monkeypatch.setattr(grader, "VERILATOR", "verilator-yang-tidak-ada")

    assert grader.run_lint(tmp_path, "counter4") == ""
