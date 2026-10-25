from collections.abc import Iterator

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db import init_db, make_engine
from app.models import (
    ExerciseProgress,
    ExerciseStatus,
    File,
    Project,
    ProjectKind,
    Run,
    RunStatus,
)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = make_engine("sqlite://")
    init_db(engine)
    with Session(engine) as s:
        yield s


def test_project_with_files_round_trip(session: Session) -> None:
    project = Project(name="Counter", kind=ProjectKind.exercise, source="counter-4bit")
    session.add(project)
    session.commit()
    session.refresh(project)
    assert project.id is not None
    assert project.created_at is not None

    session.add(File(project_id=project.id, path="rtl/top.v", content="module top; endmodule"))
    session.commit()

    files = session.exec(select(File).where(File.project_id == project.id)).all()
    assert [f.path for f in files] == ["rtl/top.v"]


def test_file_path_is_unique_per_project(session: Session) -> None:
    project = Project(name="P", kind=ProjectKind.sandbox)
    session.add(project)
    session.commit()
    session.refresh(project)
    assert project.id is not None

    session.add(File(project_id=project.id, path="a.v", content=""))
    session.commit()
    session.add(File(project_id=project.id, path="a.v", content="dup"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_run_defaults_and_json_fields(session: Session) -> None:
    run = Run(kind="echo", params={"args": ["-V"]})
    session.add(run)
    session.commit()

    loaded = session.get(Run, run.id)
    assert loaded is not None
    assert len(loaded.id) == 32  # uuid4 hex
    assert loaded.status == RunStatus.queued
    assert loaded.params == {"args": ["-V"]}
    assert loaded.result is None
    assert loaded.project_id is None
    assert loaded.started_at is None


def test_run_ids_are_unique(session: Session) -> None:
    assert Run(kind="echo").id != Run(kind="echo").id


def test_exercise_progress_defaults(session: Session) -> None:
    session.add(ExerciseProgress(exercise_id="counter-4bit"))
    session.commit()

    p = session.get(ExerciseProgress, "counter-4bit")
    assert p is not None
    assert p.status == ExerciseStatus.not_started
    assert p.attempts == 0
    assert p.hints_opened == 0
    assert p.last_code is None
    assert p.solved_at is None
