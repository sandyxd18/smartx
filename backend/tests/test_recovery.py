from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import Settings
from app.db import init_db, make_engine
from app.jobs.fake_runner import FakeRunner
from app.jobs.recovery import RESTART_ERROR, recover_interrupted_runs
from app.main import create_app
from app.models import Run, RunStatus


def test_recover_marks_unfinished_runs_failed() -> None:
    engine = make_engine("sqlite://")
    init_db(engine)
    with Session(engine) as s:
        runs = {
            status: Run(kind="echo", status=status)
            for status in (RunStatus.queued, RunStatus.running, RunStatus.succeeded)
        }
        s.add_all(runs.values())
        s.commit()
        ids = {status: run.id for status, run in runs.items()}

    assert recover_interrupted_runs(engine) == 2

    with Session(engine) as s:
        for status in (RunStatus.queued, RunStatus.running):
            run = s.get(Run, ids[status])
            assert run is not None
            assert run.status == RunStatus.failed
            assert run.error == RESTART_ERROR
            assert run.finished_at is not None
        done = s.get(Run, ids[RunStatus.succeeded])
        assert done is not None and done.status == RunStatus.succeeded and done.error is None


def test_app_startup_recovers_runs_and_removes_orphans(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True)
    engine = make_engine(f"sqlite:///{settings.db_path.as_posix()}")
    init_db(engine)
    with Session(engine) as s:
        run = Run(kind="echo", status=RunStatus.running)
        s.add(run)
        s.commit()
        run_id = run.id
    engine.dispose()

    runner = FakeRunner()
    with TestClient(create_app(settings, runner=runner)) as client:
        assert client.app.state.queue is not None  # type: ignore[attr-defined]

    engine = make_engine(f"sqlite:///{settings.db_path.as_posix()}")
    with Session(engine) as s:
        run = s.get(Run, run_id)
        assert run is not None
        assert run.status == RunStatus.failed
        assert run.error == RESTART_ERROR
    engine.dispose()
    assert runner.orphans_removed == 1
