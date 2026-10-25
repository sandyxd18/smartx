import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.config import REPO_ROOT
from app.content import ExerciseCatalog
from tests.helpers import write_exercise


def bump_mtime(path: Path) -> None:
    # Filesystem mtime resolution can be coarse; make the change unmistakable.
    st = path.stat()
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 2_000_000_000))


@pytest.fixture
def root(tmp_path: Path) -> Path:
    r = tmp_path / "exercises"
    r.mkdir()
    return r


def test_loads_valid_exercise(root: Path) -> None:
    d = write_exercise(root, "mux-2to1", topics=["combinational", "mux"], level=2, order=20)
    (d / "README.md").write_text("# Mux 2:1\n", encoding="utf-8")
    (d / "starter.v").write_text("module top; endmodule\n", encoding="utf-8")

    catalog = ExerciseCatalog(root)
    ex = catalog.get("mux-2to1")

    assert catalog.errors == []
    assert ex is not None
    assert ex.meta.title == "Soal mux-2to1"
    assert ex.meta.topics == ["combinational", "mux"]
    assert ex.meta.level == 2
    assert ex.meta.order == 20
    assert ex.meta.requires == []
    assert ex.meta.hints == ["petunjuk 1", "petunjuk 2"]
    assert ex.read_statement() == "# Mux 2:1\n"
    assert ex.read_starter() == "module top; endmodule\n"
    assert ex.solution_path == d / "solution.v"
    assert ex.test_path == d / "test_top.py"


def test_repo_content_is_valid() -> None:
    catalog = ExerciseCatalog(REPO_ROOT / "content" / "exercises")
    assert catalog.errors == []
    ex = catalog.get("counter-4bit")
    assert ex is not None
    assert ex.meta.toplevel == "counter4"


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"id": "other-id"}, "nama folder"),
        ({"level": 7}, "level"),
        ({"step": 0}, "step"),
        ({"titel": "typo"}, "titel"),
        ({"topics": []}, "topics"),
        ({"toplevel": "1bad name"}, "toplevel"),
        ({"language": "vhdl"}, "language"),
        ({"timeout_s": 0}, "timeout_s"),
        ({"title": None}, "title"),
        ({"requires": ["tidak-ada"]}, "tidak-ada"),
    ],
)
def test_invalid_metadata_is_reported_and_skipped(
    root: Path, overrides: dict[str, Any], expected: str
) -> None:
    write_exercise(root, "good")
    write_exercise(root, "bad", **overrides)

    catalog = ExerciseCatalog(root)

    assert [e.id for e in catalog.all()] == ["good"]
    assert len(catalog.errors) == 1
    error = catalog.errors[0]
    assert error.folder == "bad"
    assert expected in error.message


@pytest.mark.parametrize(
    "files",
    [
        {"starter": "../starter.v"},
        {"starter": "sub/starter.v"},
        {"starter": "C:\\starter.v"},
        {"solution": ".hidden.v"},
        {"test": "missing.py"},
    ],
)
def test_bad_file_references(root: Path, files: dict[str, str]) -> None:
    base = {
        "starter": "starter.v",
        "solution": "solution.v",
        "test": "test_top.py",
        "statement": "README.md",
    }
    write_exercise(root, "bad", files={**base, **files})

    catalog = ExerciseCatalog(root)

    assert catalog.all() == []
    assert len(catalog.errors) == 1


def test_invalid_yaml_does_not_crash(root: Path) -> None:
    d = root / "broken"
    d.mkdir()
    (d / "exercise.yaml").write_text("id: broken\ntitle: [tidak ditutup\n", encoding="utf-8")

    catalog = ExerciseCatalog(root)

    assert catalog.all() == []
    assert catalog.errors[0].folder == "broken"
    assert "YAML" in catalog.errors[0].message


def test_folders_without_exercise_yaml_are_ignored(root: Path) -> None:
    write_exercise(root, "good")
    (root / "__pycache__").mkdir()
    (root / "notes.txt").write_text("x")

    catalog = ExerciseCatalog(root)

    assert [e.id for e in catalog.all()] == ["good"]
    assert catalog.errors == []


def test_requires_known_exercise(root: Path) -> None:
    write_exercise(root, "dff-basic")
    write_exercise(root, "counter", requires=["dff-basic"])

    catalog = ExerciseCatalog(root)

    assert catalog.errors == []
    counter = catalog.get("counter")
    assert counter is not None and counter.meta.requires == ["dff-basic"]


def test_sorted_by_step_then_order_then_id(root: Path) -> None:
    write_exercise(root, "b-later-step", step=2)
    write_exercise(root, "c-no-order")
    write_exercise(root, "a-no-order")
    write_exercise(root, "z-first", order=10)

    ids = [e.id for e in ExerciseCatalog(root).all()]

    assert ids == ["z-first", "a-no-order", "c-no-order", "b-later-step"]


def test_missing_root_is_empty(tmp_path: Path) -> None:
    catalog = ExerciseCatalog(tmp_path / "nope")
    assert catalog.all() == []
    assert catalog.errors == []


def test_app_exposes_catalog(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from app.config import Settings
    from app.jobs.fake_runner import FakeRunner
    from app.main import create_app

    write_exercise(tmp_path / "content" / "exercises", "mux-2to1")
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        content_dir=tmp_path / "content",
        content_auto_reload=False,
    )

    with TestClient(create_app(settings, runner=FakeRunner())) as client:
        catalog = client.app.state.catalog  # type: ignore[attr-defined]
        assert isinstance(catalog, ExerciseCatalog)
        assert [e.id for e in catalog.all()] == ["mux-2to1"]


class TestReload:
    def test_picks_up_edits_new_and_removed_exercises(self, root: Path) -> None:
        d = write_exercise(root, "first")
        catalog = ExerciseCatalog(root, auto_reload=True)
        assert [e.meta.title for e in catalog.all()] == ["Soal first"]

        meta = yaml.safe_load((d / "exercise.yaml").read_text(encoding="utf-8"))
        meta["title"] = "Judul baru"
        (d / "exercise.yaml").write_text(yaml.safe_dump(meta), encoding="utf-8")
        bump_mtime(d / "exercise.yaml")
        assert [e.meta.title for e in catalog.all()] == ["Judul baru"]

        write_exercise(root, "second")
        assert [e.id for e in catalog.all()] == ["first", "second"]

        for f in d.iterdir():
            f.unlink()
        d.rmdir()
        assert [e.id for e in catalog.all()] == ["second"]

    def test_disabled_reload_keeps_cache(self, root: Path) -> None:
        write_exercise(root, "first")
        catalog = ExerciseCatalog(root, auto_reload=False)
        assert len(catalog.all()) == 1

        write_exercise(root, "second")

        assert len(catalog.all()) == 1
        catalog.reload()
        assert len(catalog.all()) == 2

    def test_statement_is_always_read_fresh(self, root: Path) -> None:
        d = write_exercise(root, "first")
        catalog = ExerciseCatalog(root, auto_reload=False)
        ex = catalog.get("first")
        assert ex is not None

        (d / "README.md").write_text("versi baru\n", encoding="utf-8")

        assert ex.read_statement() == "versi baru\n"
