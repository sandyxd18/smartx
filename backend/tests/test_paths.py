import os
from pathlib import Path

import pytest

from app.paths import UnsafePathError, safe_join


@pytest.fixture
def base(tmp_path: Path) -> Path:
    base = tmp_path / "runs" / "r1"
    (base / "sim_build").mkdir(parents=True)
    (base / "sim_build" / "dump.fst").write_text("wave")
    (tmp_path / "secret.txt").write_text("secret")
    return base


@pytest.mark.parametrize(
    "user_path",
    ["run.log", "sim_build/dump.fst", "sim_build\\dump.fst", "./run.log", "a//b.txt"],
)
def test_accepts_paths_inside_base(base: Path, user_path: str) -> None:
    result = safe_join(base, user_path)
    assert result.is_relative_to(base.resolve())


@pytest.mark.parametrize(
    "user_path",
    [
        "",
        "..",
        "../secret.txt",
        "../../secret.txt",
        "sim_build/../../secret.txt",
        "..\\..\\secret.txt",
        "/etc/passwd",
        "\\Windows\\win.ini",
        "C:/Windows/win.ini",
        "C:secret.txt",
        "//server/share/x",
        "run.log\x00.png",
    ],
)
def test_rejects_escaping_paths(base: Path, user_path: str) -> None:
    with pytest.raises(UnsafePathError):
        safe_join(base, user_path)


def test_rejects_symlink_escaping_base(base: Path, tmp_path: Path) -> None:
    try:
        os.symlink(tmp_path / "secret.txt", base / "link.txt")
    except OSError:
        pytest.skip("creating symlinks is not permitted here")
    with pytest.raises(UnsafePathError):
        safe_join(base, "link.txt")
