import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi import Path as PathParam
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from sqlmodel import Session
from sse_starlette import EventSourceResponse, ServerSentEvent

from app.config import Settings
from app.db import get_session
from app.jobs.events import EventHub
from app.jobs.kinds import KINDS
from app.jobs.queue import JobQueue
from app.jobs.stream import TERMINAL_STATUSES, follow_run
from app.models import Run, RunStatus
from app.paths import UnsafePathError, safe_join

router = APIRouter(prefix="/runs", tags=["runs"])

RunId = Annotated[str, PathParam(pattern=r"^[0-9a-f]{32}$")]
SessionDep = Annotated[Session, Depends(get_session)]

NOT_FOUND = "Run tidak ditemukan."


def get_queue(request: Request) -> JobQueue:
    return request.app.state.queue  # type: ignore[no-any-return]


def get_events(request: Request) -> EventHub:
    return request.app.state.events  # type: ignore[no-any-return]


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]


class RunCreate(BaseModel):
    # Only the smoke-test job for now; real kinds get their own endpoints (exercises, projects).
    kind: Literal["echo"]
    params: dict[str, Any] = {}


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: int | None
    kind: str
    status: RunStatus
    params: dict[str, Any]
    result: dict[str, Any] | None
    tool_versions: dict[str, Any] | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    exit_code: int | None
    error: str | None

    @field_validator("created_at", "started_at", "finished_at")
    @classmethod
    def _assume_utc(cls, value: datetime | None) -> datetime | None:
        # SQLite drops tzinfo; all timestamps are stored in UTC.
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


def _get_run(session: Session, run_id: str) -> Run:
    run = session.get(Run, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return run


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_run(
    body: RunCreate, session: SessionDep, queue: Annotated[JobQueue, Depends(get_queue)]
) -> RunRead:
    try:
        params = KINDS[body.kind].Params.model_validate(body.params).model_dump()
    except ValidationError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, json.loads(exc.json(include_url=False))
        ) from exc
    run = Run(kind=body.kind, params=params)
    session.add(run)
    session.commit()
    session.refresh(run)
    queue.submit(run.id)
    return RunRead.model_validate(run)


@router.get("/{run_id}")
def get_run(run_id: RunId, session: SessionDep) -> RunRead:
    return RunRead.model_validate(_get_run(session, run_id))


@router.post("/{run_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_run(
    run_id: RunId, session: SessionDep, queue: Annotated[JobQueue, Depends(get_queue)]
) -> RunRead:
    run = _get_run(session, run_id)
    if run.status in TERMINAL_STATUSES or not await queue.cancel(run_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Run sudah selesai.")
    session.refresh(run)
    return RunRead.model_validate(run)


@router.get(
    "/{run_id}/events",
    response_class=EventSourceResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def run_events(
    run_id: RunId,
    request: Request,
    session: SessionDep,
    events: Annotated[EventHub, Depends(get_events)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> EventSourceResponse:
    """SSE: `log` events ({line}) and `status` events ({status}); ends at a final status."""
    _get_run(session, run_id)

    async def stream() -> AsyncIterator[ServerSentEvent]:
        async for event in follow_run(
            run_id,
            engine=request.app.state.engine,
            events=events,
            run_dir=settings.runs_dir / run_id,
        ):
            payload = {k: v for k, v in event.items() if k != "type"}
            yield ServerSentEvent(json.dumps(payload, ensure_ascii=False), event=event["type"])

    return EventSourceResponse(stream(), ping=15)


@router.get("/{run_id}/files/{path:path}")
def get_run_file(
    run_id: RunId,
    path: str,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> FileResponse:
    _get_run(session, run_id)
    try:
        target = safe_join(settings.runs_dir / run_id, path)
    except UnsafePathError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Path tidak valid: {exc}") from exc
    if not target.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File tidak ditemukan.")
    return FileResponse(target)
