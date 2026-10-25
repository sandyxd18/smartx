"""Database tables. See docs/ARCHITECTURE.md, section "Model data"."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class ProjectKind(StrEnum):
    exercise = "exercise"
    sandbox = "sandbox"
    guided = "guided"
    tt = "tt"


class RunStatus(StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"
    timeout = "timeout"


class ExerciseStatus(StrEnum):
    not_started = "not_started"
    attempted = "attempted"
    solved = "solved"


class Project(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    kind: ProjectKind
    # exercise_id or guided project id this project was created from.
    source: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class File(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("project_id", "path"),)

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    path: str
    content: str = ""
    updated_at: datetime = Field(default_factory=utcnow)


class Run(SQLModel, table=True):
    # Random ids so run folders under data/runs/ never collide after a DB reset.
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    project_id: int | None = Field(default=None, foreign_key="project.id", index=True)
    kind: str
    status: RunStatus = RunStatus.queued
    params: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    result: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    tool_versions: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    exit_code: int | None = None
    error: str | None = None


class ExerciseProgress(SQLModel, table=True):
    exercise_id: str = Field(primary_key=True)
    status: ExerciseStatus = ExerciseStatus.not_started
    attempts: int = 0
    last_code: str | None = None
    solved_at: datetime | None = None
    hints_opened: int = 0
