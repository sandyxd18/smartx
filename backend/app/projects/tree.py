"""A project's file tree, stored as File and Folder rows.

Every folder has a row (also the parents of every file), so deleting the last file in a
folder keeps the folder. Paths are unique case-insensitively, because a run writes them
to a folder that may sit on a case-insensitive Windows disk.
"""

from dataclasses import dataclass
from typing import Literal

from sqlmodel import Session, col, select

from app.models import File, Folder, utcnow
from app.projects.paths import ancestors, normalize_project_path

MAX_ENTRIES = 300  # files + folders per project
MAX_FILE_CHARS = 500_000

EntryKind = Literal["file", "dir"]


class TreeError(Exception):
    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EntryNotFound(TreeError):
    status_code = 404


class EntryConflict(TreeError):
    status_code = 409


class TreeLimit(TreeError):
    status_code = 422


@dataclass(frozen=True)
class Entry:
    path: str
    kind: EntryKind


def _files(session: Session, project_id: int) -> list[File]:
    return list(session.exec(select(File).where(File.project_id == project_id)))


def _folders(session: Session, project_id: int) -> list[Folder]:
    return list(session.exec(select(Folder).where(Folder.project_id == project_id)))


def list_entries(session: Session, project_id: int) -> list[Entry]:
    """Folders and files, sorted by path (a folder comes right before its contents)."""
    items = [Entry(f.path, "dir") for f in _folders(session, project_id)]
    items += [Entry(f.path, "file") for f in _files(session, project_id)]
    return sorted(items, key=lambda e: e.path.lower().split("/"))


def _occupied(session: Session, project_id: int) -> dict[str, Entry]:
    return {e.path.lower(): e for e in list_entries(session, project_id)}


def _inside(path: str, folder: str) -> bool:
    return path.lower().startswith(folder.lower() + "/")


def _check_free(occupied: dict[str, Entry], path: str, ignore: str | None = None) -> None:
    """path must not exist (case-insensitively) and no parent of it may be a file."""
    existing = occupied.get(path.lower())
    if existing is not None and existing.path != ignore:
        what = "Folder" if existing.kind == "dir" else "File"
        raise EntryConflict(f"{what} '{existing.path}' sudah ada.")
    for parent in ancestors(path):
        found = occupied.get(parent.lower())
        if found is not None and found.kind == "file":
            raise EntryConflict(f"'{found.path}' adalah file, bukan folder.")


def _check_room(occupied: dict[str, Entry], new_entries: int) -> None:
    if len(occupied) + new_entries > MAX_ENTRIES:
        raise TreeLimit(f"Proyek sudah berisi batas maksimal {MAX_ENTRIES} file dan folder.")


def _check_size(content: str) -> None:
    if len(content) > MAX_FILE_CHARS:
        raise TreeLimit(f"File terlalu besar (maksimal {MAX_FILE_CHARS} karakter).")


def _missing_parents(occupied: dict[str, Entry], path: str) -> list[str]:
    return [p for p in ancestors(path) if p.lower() not in occupied]


def _add_folders(session: Session, project_id: int, paths: list[str]) -> None:
    for path in paths:
        session.add(Folder(project_id=project_id, path=path))


def get_file(session: Session, project_id: int, raw_path: str) -> File:
    path = normalize_project_path(raw_path)
    found = session.exec(
        select(File).where(File.project_id == project_id, File.path == path)
    ).first()
    if found is None:
        raise EntryNotFound(f"File '{path}' tidak ditemukan.")
    return found


def create_file(session: Session, project_id: int, raw_path: str, content: str = "") -> File:
    """Add a new file (and its missing parent folders); the path must be free."""
    path = normalize_project_path(raw_path)
    _check_size(content)
    occupied = _occupied(session, project_id)
    _check_free(occupied, path)
    parents = _missing_parents(occupied, path)
    _check_room(occupied, 1 + len(parents))
    _add_folders(session, project_id, parents)
    file = File(project_id=project_id, path=path, content=content)
    session.add(file)
    return file


def write_file(session: Session, project_id: int, raw_path: str, content: str) -> File:
    """Replace a file's content, creating the file if it does not exist yet."""
    path = normalize_project_path(raw_path)
    _check_size(content)
    try:
        file = get_file(session, project_id, path)
    except EntryNotFound:
        return create_file(session, project_id, path, content)
    file.content = content
    file.updated_at = utcnow()
    session.add(file)
    return file


def create_folder(session: Session, project_id: int, raw_path: str) -> None:
    path = normalize_project_path(raw_path)
    occupied = _occupied(session, project_id)
    _check_free(occupied, path)
    new = [*_missing_parents(occupied, path), path]
    _check_room(occupied, len(new))
    _add_folders(session, project_id, new)


def delete_entry(session: Session, project_id: int, raw_path: str) -> None:
    """Delete a file, or a folder with everything inside it."""
    path = normalize_project_path(raw_path)
    files = _files(session, project_id)
    folders = _folders(session, project_id)
    doomed: list[File | Folder] = [f for f in files if f.path == path]
    if not doomed:
        doomed = [f for f in folders if f.path == path]
        if not doomed:
            raise EntryNotFound(f"'{path}' tidak ditemukan.")
        doomed += [f for f in [*files, *folders] if f.path.startswith(path + "/")]
    for row in doomed:
        session.delete(row)


def move_entry(session: Session, project_id: int, raw_src: str, raw_dst: str) -> None:
    """Rename or move a file or folder (with its contents)."""
    src = normalize_project_path(raw_src)
    dst = normalize_project_path(raw_dst)
    occupied = _occupied(session, project_id)
    entry = occupied.get(src.lower())
    if entry is None or entry.path != src:
        raise EntryNotFound(f"'{src}' tidak ditemukan.")
    if entry.kind == "dir" and _inside(dst, src):
        raise EntryConflict("Folder tidak bisa dipindah ke dalam dirinya sendiri.")
    if dst == src:
        return
    # A case-only rename ('alu.v' -> 'ALU.v') is allowed: it only clashes with itself.
    _check_free(occupied, dst, ignore=src)
    parents = _missing_parents(occupied, dst)
    _check_room(occupied, len(parents))
    _add_folders(session, project_id, parents)

    def renamed(path: str) -> str:
        return dst + path[len(src) :]

    for row in [*_files(session, project_id), *_folders(session, project_id)]:
        if row.path == src or (entry.kind == "dir" and row.path.startswith(src + "/")):
            row.path = renamed(row.path)
            if isinstance(row, File):
                row.updated_at = utcnow()
            session.add(row)


def delete_tree(session: Session, project_id: int) -> None:
    for row in [*_files(session, project_id), *_folders(session, project_id)]:
        session.delete(row)


def read_all(session: Session, project_id: int) -> dict[str, str]:
    """Every file's content by path."""
    return {f.path: f.content for f in _files(session, project_id)}


def file_count(session: Session, project_id: int) -> int:
    return len(session.exec(select(col(File.id)).where(File.project_id == project_id)).all())
