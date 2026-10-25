from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, ValidationError
from sqlmodel import Session, select

from app.api.runs import RunRead, get_app_settings, get_queue
from app.config import Settings
from app.content import Exercise, ExerciseCatalog
from app.db import get_session
from app.jobs.kinds.grade import MAX_CODE_CHARS, GradeResult
from app.jobs.queue import JobQueue
from app.models import ExerciseProgress, ExerciseStatus, Run
from app.progress import (
    GRADE_KIND,
    latest_grade_run,
    load_progress,
    record_submission,
    save_code,
    solution_unlocked,
)

router = APIRouter(prefix="/exercises", tags=["exercises"])

SessionDep = Annotated[Session, Depends(get_session)]
NOT_FOUND = "Soal tidak ditemukan."


def get_catalog(request: Request) -> ExerciseCatalog:
    return request.app.state.catalog  # type: ignore[no-any-return]


CatalogDep = Annotated[ExerciseCatalog, Depends(get_catalog)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]


class ExerciseSummary(BaseModel):
    id: str
    title: str
    step: int
    level: int
    topics: list[str]
    order: int | None
    requires: list[str]
    status: ExerciseStatus
    attempts: int


class ExerciseRunRead(RunRead):
    """A grade run with its result parsed (None until the grader has finished)."""

    grade: GradeResult | None


class ExerciseDetail(ExerciseSummary):
    toplevel: str
    language: Literal["verilog", "systemverilog"]
    statement: str  # Markdown
    starter: str
    code: str  # last submitted code, or the starter
    hints: list[str]  # only the hints opened so far
    hints_total: int
    solution_available: bool
    solution_unlock_attempts: int
    last_run: ExerciseRunRead | None


class ExerciseRunCreate(BaseModel):
    code: str = Field(max_length=MAX_CODE_CHARS)


class ExerciseCodeSave(BaseModel):
    code: str = Field(max_length=MAX_CODE_CHARS)


class HintsRead(BaseModel):
    hints: list[str]
    total: int


class SolutionRead(BaseModel):
    code: str


def _get_exercise(catalog: ExerciseCatalog, exercise_id: str) -> Exercise:
    exercise = catalog.get(exercise_id)
    if exercise is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return exercise


def _summary(exercise: Exercise, progress: ExerciseProgress) -> ExerciseSummary:
    m = exercise.meta
    return ExerciseSummary(
        id=m.id,
        title=m.title,
        step=m.step,
        level=m.level,
        topics=m.topics,
        order=m.order,
        requires=m.requires,
        status=progress.status,
        attempts=progress.attempts,
    )


def _exercise_run(run: Run) -> ExerciseRunRead:
    grade: GradeResult | None = None
    if run.result is not None:
        try:
            grade = GradeResult.model_validate(run.result)
        except ValidationError:
            grade = None  # e.g. results stored before GradeResult existed
    return ExerciseRunRead(**RunRead.model_validate(run).model_dump(), grade=grade)


def _opened_hints(exercise: Exercise, progress: ExerciseProgress) -> list[str]:
    return exercise.meta.hints[: progress.hints_opened]


@router.get("")
def list_exercises(session: SessionDep, catalog: CatalogDep) -> list[ExerciseSummary]:
    progress = {p.exercise_id: p for p in session.exec(select(ExerciseProgress)).all()}
    return [
        _summary(ex, progress.get(ex.id) or ExerciseProgress(exercise_id=ex.id))
        for ex in catalog.all()
    ]


@router.get("/{exercise_id}")
def get_exercise(
    exercise_id: str, session: SessionDep, catalog: CatalogDep, settings: SettingsDep
) -> ExerciseDetail:
    exercise = _get_exercise(catalog, exercise_id)
    progress = load_progress(session, exercise_id)
    starter = exercise.read_starter()
    last_run = latest_grade_run(session, exercise_id)
    return ExerciseDetail(
        **_summary(exercise, progress).model_dump(),
        toplevel=exercise.meta.toplevel,
        language=exercise.meta.language,
        statement=exercise.read_statement(),
        starter=starter,
        code=progress.last_code if progress.last_code is not None else starter,
        hints=_opened_hints(exercise, progress),
        hints_total=len(exercise.meta.hints),
        solution_available=solution_unlocked(progress, settings.solution_unlock_attempts),
        solution_unlock_attempts=settings.solution_unlock_attempts,
        last_run=_exercise_run(last_run) if last_run else None,
    )


@router.post("/{exercise_id}/runs", status_code=status.HTTP_201_CREATED)
async def run_exercise(
    exercise_id: str,
    body: ExerciseRunCreate,
    session: SessionDep,
    catalog: CatalogDep,
    queue: Annotated[JobQueue, Depends(get_queue)],
) -> ExerciseRunRead:
    _get_exercise(catalog, exercise_id)
    run = Run(kind=GRADE_KIND, params={"exercise_id": exercise_id, "code": body.code})
    session.add(run)
    record_submission(session, exercise_id, body.code)
    session.commit()
    session.refresh(run)
    queue.submit(run.id)
    return _exercise_run(run)


@router.get("/{exercise_id}/runs/{run_id}")
def get_exercise_run(
    exercise_id: str, run_id: str, session: SessionDep, catalog: CatalogDep
) -> ExerciseRunRead:
    _get_exercise(catalog, exercise_id)
    run = session.get(Run, run_id)
    if run is None or run.kind != GRADE_KIND or run.params.get("exercise_id") != exercise_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run tidak ditemukan.")
    return _exercise_run(run)


@router.put("/{exercise_id}/code", status_code=status.HTTP_204_NO_CONTENT)
def save_exercise_code(
    exercise_id: str, body: ExerciseCodeSave, session: SessionDep, catalog: CatalogDep
) -> None:
    """Autosave of the editor. Does not count as an attempt."""
    _get_exercise(catalog, exercise_id)
    save_code(session, exercise_id, body.code)


@router.post("/{exercise_id}/hints/next")
def open_next_hint(exercise_id: str, session: SessionDep, catalog: CatalogDep) -> HintsRead:
    exercise = _get_exercise(catalog, exercise_id)
    progress = load_progress(session, exercise_id)
    total = len(exercise.meta.hints)
    if progress.hints_opened < total:
        progress.hints_opened += 1
        session.add(progress)
        session.commit()
    return HintsRead(hints=_opened_hints(exercise, progress), total=total)


@router.get(
    "/{exercise_id}/solution",
    responses={403: {"description": "Solusi belum terbuka"}},
)
def get_solution(
    exercise_id: str, session: SessionDep, catalog: CatalogDep, settings: SettingsDep
) -> SolutionRead:
    """The only endpoint that ever returns solution.v."""
    exercise = _get_exercise(catalog, exercise_id)
    progress = load_progress(session, exercise_id)
    if not solution_unlocked(progress, settings.solution_unlock_attempts):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Solusi terbuka setelah soal lulus atau setelah "
            f"{settings.solution_unlock_attempts} percobaan (sekarang {progress.attempts}).",
        )
    return SolutionRead(code=exercise.solution_path.read_text(encoding="utf-8"))
