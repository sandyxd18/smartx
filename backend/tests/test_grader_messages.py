"""tools/grader/grade.py runs inside the toolchain image; its pure helpers are tested here."""

import importlib.util
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
