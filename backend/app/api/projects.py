"""Sandbox projects: create from a template or an exercise, and edit the file tree."""

import shutil
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator
from sqlmodel import Session, col, func, select

from app.api.exercises import CatalogDep
from app.api.runs import get_app_settings
from app.config import Settings
from app.content.models import ExerciseId
from app.db import get_session
from app.models import File, Project, ProjectKind, Run, RunStatus
from app.progress import load_progress
from app.projects import tree
from app.projects.paths import InvalidProjectPath
from app.projects.templates import exercise_files, load_templates

router = APIRouter(tags=["projects"])

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]
NOT_FOUND = "Proyek tidak ditemukan."

ProjectName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
TemplateId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]
FileContent = Annotated[str, Field(max_length=tree.MAX_FILE_CHARS)]


def _utc(value: datetime) -> datetime:
    # SQLite drops tzinfo; all timestamps are stored in UTC.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class ProjectTemplateRead(BaseModel):
    id: str
    title: str
    description: str


class ProjectCreate(BaseModel):
    """Exactly one of template and exercise_id."""

    name: ProjectName
    template: TemplateId | None = None
    exercise_id: ExerciseId | None = None

    @model_validator(mode="after")
    def _one_source(self) -> "ProjectCreate":
        if (self.template is None) == (self.exercise_id is None):
            raise ValueError("Pilih satu: template atau exercise_id.")
        return self


class ProjectUpdate(BaseModel):
    name: ProjectName


class ProjectSummary(BaseModel):
    id: int
    name: str
    kind: ProjectKind
    source: str | None
    created_at: datetime
    updated_at: datetime  # latest file change, or created_at
    file_count: int

    @field_validator("created_at", "updated_at")
    @classmethod
    def _assume_utc(cls, value: datetime) -> datetime:
        return _utc(value)


class EntryRead(BaseModel):
    path: str
    kind: Literal["file", "dir"]


class ProjectDetail(ProjectSummary):
    entries: list[EntryRead]  # sorted by path; folders before their contents


class FileRead(BaseModel):
    path: str
    content: str
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def _assume_utc(cls, value: datetime) -> datetime:
        return _utc(value)


class FileCreate(BaseModel):
    path: str
    content: FileContent = ""


class FileWrite(BaseModel):
    content: FileContent


class FolderCreate(BaseModel):
    path: str


class MoveRequest(BaseModel):
    from_path: str
    to_path: str


def _tree_errors(exc: InvalidProjectPath | tree.TreeError) -> HTTPException:
    if isinstance(exc, InvalidProjectPath):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))
    return HTTPException(exc.status_code, exc.message)


def _get_project(session: Session, project_id: int) -> Project:
    project = session.get(Project, project_id)
    if project is None or project.kind != ProjectKind.sandbox:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return project


def _summary(session: Session, project: Project) -> ProjectSummary:
    assert project.id is not None
    latest = session.exec(
        select(func.max(File.updated_at)).where(File.project_id == project.id)
    ).one()
    return ProjectSummary(
        id=project.id,
        name=project.name,
        kind=project.kind,
        source=project.source,
        created_at=project.created_at,
        updated_at=max(_utc(latest), _utc(project.created_at)) if latest else project.created_at,
        file_count=tree.file_count(session, project.id),
    )


def _detail(session: Session, project: Project) -> ProjectDetail:
    assert project.id is not None
    entries = [EntryRead(path=e.path, kind=e.kind) for e in tree.list_entries(session, project.id)]
    return ProjectDetail(**_summary(session, project).model_dump(), entries=entries)


def _file_read(file: File) -> FileRead:
    return FileRead(path=file.path, content=file.content, updated_at=file.updated_at)


@router.get("/project-templates")
def list_templates(settings: SettingsDep) -> list[ProjectTemplateRead]:
    return [
        ProjectTemplateRead(id=t.id, title=t.meta.title, description=t.meta.description)
        for t in load_templates(settings.content_dir / "templates")
    ]


@router.get("/projects")
def list_projects(session: SessionDep) -> list[ProjectSummary]:
    projects = session.exec(
        select(Project)
        .where(Project.kind == ProjectKind.sandbox)
        .order_by(col(Project.created_at).desc(), col(Project.id).desc())
    )
    return [_summary(session, p) for p in projects]


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate, session: SessionDep, settings: SettingsDep, catalog: CatalogDep
) -> ProjectDetail:
    if body.template is not None:
        found = [
            t for t in load_templates(settings.content_dir / "templates") if t.id == body.template
        ]
        if not found:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Template tidak ditemukan.")
        files = found[0].files()
        source = f"template:{body.template}"
    else:
        assert body.exercise_id is not None
        exercise = catalog.get(body.exercise_id)
        if exercise is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Soal tidak ditemukan.")
        code = load_progress(session, exercise.id).last_code
        files = exercise_files(exercise, code if code is not None else exercise.read_starter())
        source = f"exercise:{exercise.id}"

    project = Project(name=body.name, kind=ProjectKind.sandbox, source=source)
    session.add(project)
    session.flush()
    assert project.id is not None
    try:
        for path, content in files.items():
            tree.create_file(session, project.id, path, content)
            session.flush()
    except (InvalidProjectPath, tree.TreeError) as exc:
        raise _tree_errors(exc) from exc
    session.commit()
    session.refresh(project)
    return _detail(session, project)


@router.get("/projects/{project_id}")
def get_project(project_id: int, session: SessionDep) -> ProjectDetail:
    return _detail(session, _get_project(session, project_id))


@router.patch("/projects/{project_id}")
def update_project(project_id: int, body: ProjectUpdate, session: SessionDep) -> ProjectDetail:
    project = _get_project(session, project_id)
    project.name = body.name
    session.add(project)
    session.commit()
    session.refresh(project)
    return _detail(session, project)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, session: SessionDep, settings: SettingsDep) -> None:
    project = _get_project(session, project_id)
    runs = list(session.exec(select(Run).where(Run.project_id == project_id)))
    if any(r.status in (RunStatus.queued, RunStatus.running) for r in runs):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Masih ada run yang berjalan di proyek ini. Batalkan atau tunggu sampai selesai.",
        )
    for run in runs:
        session.delete(run)
    tree.delete_tree(session, project_id)
    session.delete(project)
    session.commit()
    for run in runs:  # run ids are random hex, never user input
        shutil.rmtree(settings.runs_dir / run.id, ignore_errors=True)


@router.get("/projects/{project_id}/files/{path:path}")
def read_file(project_id: int, path: str, session: SessionDep) -> FileRead:
    _get_project(session, project_id)
    try:
        return _file_read(tree.get_file(session, project_id, path))
    except (InvalidProjectPath, tree.TreeError) as exc:
        raise _tree_errors(exc) from exc


@router.post("/projects/{project_id}/files", status_code=status.HTTP_201_CREATED)
def create_file(project_id: int, body: FileCreate, session: SessionDep) -> FileRead:
    _get_project(session, project_id)
    try:
        file = tree.create_file(session, project_id, body.path, body.content)
    except (InvalidProjectPath, tree.TreeError) as exc:
        raise _tree_errors(exc) from exc
    session.commit()
    session.refresh(file)
    return _file_read(file)


@router.put("/projects/{project_id}/files/{path:path}")
def write_file(project_id: int, path: str, body: FileWrite, session: SessionDep) -> FileRead:
    """Save a file (the editor's autosave); creates it when missing."""
    _get_project(session, project_id)
    try:
        file = tree.write_file(session, project_id, path, body.content)
    except (InvalidProjectPath, tree.TreeError) as exc:
        raise _tree_errors(exc) from exc
    session.commit()
    session.refresh(file)
    return _file_read(file)


@router.delete("/projects/{project_id}/files/{path:path}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(project_id: int, path: str, session: SessionDep) -> None:
    """Delete a file, or a folder with everything in it."""
    _get_project(session, project_id)
    try:
        tree.delete_entry(session, project_id, path)
    except (InvalidProjectPath, tree.TreeError) as exc:
        raise _tree_errors(exc) from exc
    session.commit()


@router.post("/projects/{project_id}/folders", status_code=status.HTTP_201_CREATED)
def create_folder(project_id: int, body: FolderCreate, session: SessionDep) -> ProjectDetail:
    project = _get_project(session, project_id)
    try:
        tree.create_folder(session, project_id, body.path)
    except (InvalidProjectPath, tree.TreeError) as exc:
        raise _tree_errors(exc) from exc
    session.commit()
    return _detail(session, project)


@router.post("/projects/{project_id}/move")
def move_entry(project_id: int, body: MoveRequest, session: SessionDep) -> ProjectDetail:
    """Rename or move a file or folder."""
    project = _get_project(session, project_id)
    try:
        tree.move_entry(session, project_id, body.from_path, body.to_path)
    except (InvalidProjectPath, tree.TreeError) as exc:
        raise _tree_errors(exc) from exc
    session.commit()
    return _detail(session, project)
