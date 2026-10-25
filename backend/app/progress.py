"""Exercise progress: attempts, last code, hints, and when the solution may be shown."""

from sqlalchemy import Engine
from sqlmodel import Session, col, select

from app.models import ExerciseProgress, ExerciseStatus, Run, RunStatus, utcnow

GRADE_KIND = "grade"


def load_progress(session: Session, exercise_id: str) -> ExerciseProgress:
    """The stored progress, or a fresh (unsaved) one for an exercise never touched."""
    return session.get(ExerciseProgress, exercise_id) or ExerciseProgress(exercise_id=exercise_id)


def record_submission(session: Session, exercise_id: str, code: str) -> ExerciseProgress:
    """Count a Run click. The caller commits together with the new Run."""
    progress = load_progress(session, exercise_id)
    progress.attempts += 1
    progress.last_code = code
    if progress.status != ExerciseStatus.solved:
        progress.status = ExerciseStatus.attempted
    session.add(progress)
    return progress


def save_code(session: Session, exercise_id: str, code: str) -> None:
    """Autosave from the editor: keep the draft, but it is not an attempt."""
    progress = load_progress(session, exercise_id)
    progress.last_code = code
    session.add(progress)
    session.commit()


def record_run_result(engine: Engine, run_id: str) -> None:
    """Mark the exercise solved when a grade run passed. Called by the queue when a run ends."""
    with Session(engine) as session:
        run = session.get(Run, run_id)
        if run is None or run.kind != GRADE_KIND or run.status != RunStatus.succeeded:
            return
        if (run.result or {}).get("status") != "pass":
            return
        progress = load_progress(session, run.params["exercise_id"])
        if progress.status == ExerciseStatus.solved:
            return  # keep the first solved_at
        progress.status = ExerciseStatus.solved
        progress.solved_at = utcnow()
        session.add(progress)
        session.commit()


def solution_unlocked(progress: ExerciseProgress, unlock_attempts: int) -> bool:
    return progress.status == ExerciseStatus.solved or progress.attempts >= unlock_attempts


def latest_grade_run(session: Session, exercise_id: str) -> Run | None:
    statement = (
        select(Run)
        .where(Run.kind == GRADE_KIND)
        .where(col(Run.params)["exercise_id"].as_string() == exercise_id)
        .order_by(col(Run.created_at).desc())
        .limit(1)
    )
    return session.exec(statement).first()
