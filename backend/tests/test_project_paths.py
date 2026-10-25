import pytest

from app.projects.paths import (
    MAX_PATH_CHARS,
    InvalidProjectPath,
    ancestors,
    normalize_project_path,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("top.v", "top.v"),
        ("src/alu.v", "src/alu.v"),
        ("test/test_alu.py", "test/test_alu.py"),
        ("  src/fifo_sync.sv  ", "src/fifo_sync.sv"),
        ("src/", "src"),  # a folder given with a trailing slash
        ("docs/notes-v2.md", "docs/notes-v2.md"),
        ("_build/x", "_build/x"),
    ],
)
def test_accepts_plain_relative_paths(raw: str, expected: str) -> None:
    assert normalize_project_path(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "/etc/passwd",
        "../secret.v",
        "src/../../x.v",
        "src/./x.v",
        "..",
        "C:/x.v",
        "C:x.v",
        "src\\x.v",
        "\\\\server\\share\\x.v",
        "src//x.v",
        "src/x.v\x00",
        ".hidden",
        "src/.git/config",
        "src/a b.v",
        "src/x?.v",
        "src/ends-with-dot.",
        "con.v",
        "src/NUL",
        "aux.txt",
        "lpt1.v",
        "a/b/c/d/e/f/g/h/i.v",  # too deep
        "x" * (MAX_PATH_CHARS + 1),
    ],
)
def test_rejects_unsafe_paths(raw: str) -> None:
    with pytest.raises(InvalidProjectPath):
        normalize_project_path(raw)


def test_ancestors() -> None:
    assert ancestors("a/b/c.v") == ["a", "a/b"]
    assert ancestors("c.v") == []
