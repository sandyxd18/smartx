"""Startup recovery: runs that were in flight when the backend stopped can't be resumed."""

from sqlalchemy import Engine
from sqlmodel import Session, col, select

from app.models import Run, RunStatus, utcnow

RESTART_ERROR = "Backend di-restart saat run ini belum selesai."


def recover_interrupted_runs(engine: Engine) -> int:
    with Session(engine) as session:
        runs = session.exec(
            select(Run).where(col(Run.status).in_([RunStatus.queued, RunStatus.running]))
        ).all()
        for run in runs:
            run.status = RunStatus.failed
            run.error = RESTART_ERROR
            run.finished_at = utcnow()
            session.add(run)
        session.commit()
        return len(runs)
