"""In-memory catalog of content/exercises, reloaded when exercise.yaml files change."""

import logging
import threading
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.content.models import ExerciseMeta

log = logging.getLogger(__name__)

META_FILE = "exercise.yaml"

# (folder name, mtime_ns, size) of every exercise.yaml; any difference triggers a reload.
_Signature = tuple[tuple[str, int, int], ...]


@dataclass(frozen=True)
class ContentError:
    folder: str
    message: str


@dataclass(frozen=True)
class Exercise:
    meta: ExerciseMeta
    dir: Path

    @property
    def id(self) -> str:
        return self.meta.id

    @property
    def statement_path(self) -> Path:
        return self.dir / self.meta.files.statement

    @property
    def starter_path(self) -> Path:
        return self.dir / self.meta.files.starter

    @property
    def solution_path(self) -> Path:
        # Never send this file to the browser except through the solution endpoint.
        return self.dir / self.meta.files.solution

    @property
    def test_path(self) -> Path:
        return self.dir / self.meta.files.test

    # Text files are read on demand, so edits show up without a catalog reload.
    def read_statement(self) -> str:
        return self.statement_path.read_text(encoding="utf-8")

    def read_starter(self) -> str:
        return self.starter_path.read_text(encoding="utf-8")


def _format_validation_error(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors(include_url=False):
        loc = ".".join(str(p) for p in err["loc"]) or "(root)"
        parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts)


def _load_one(folder: Path) -> Exercise:
    """Parse and check one exercise folder. Raises ValueError with a readable message."""
    try:
        raw = yaml.safe_load((folder / META_FILE).read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"{META_FILE} bukan YAML yang valid: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"{META_FILE} harus berisi mapping")
    try:
        meta = ExerciseMeta.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"{META_FILE} tidak valid: {_format_validation_error(exc)}") from exc
    if meta.id != folder.name:
        raise ValueError(f"id '{meta.id}' harus sama dengan nama folder '{folder.name}'")
    exercise = Exercise(meta=meta, dir=folder)
    for key, name in meta.files.model_dump().items():
        if not (folder / name).is_file():
            raise ValueError(f"files.{key} ({name}) tidak ditemukan")
    return exercise


class ExerciseCatalog:
    def __init__(self, root: Path, *, auto_reload: bool = True) -> None:
        self._root = root
        self._auto_reload = auto_reload
        self._lock = threading.Lock()
        self._signature: _Signature | None = None
        self._exercises: dict[str, Exercise] = {}
        self._errors: list[ContentError] = []
        self.reload()

    @property
    def errors(self) -> list[ContentError]:
        self._refresh()
        return list(self._errors)

    def all(self) -> list[Exercise]:
        """Valid exercises in curriculum order: step, then `order` (unset last), then id."""
        self._refresh()
        return sorted(
            self._exercises.values(),
            key=lambda e: (e.meta.step, e.meta.order is None, e.meta.order or 0, e.id),
        )

    def get(self, exercise_id: str) -> Exercise | None:
        self._refresh()
        return self._exercises.get(exercise_id)

    def reload(self) -> None:
        with self._lock:
            self._load(self._scan_signature())

    def _refresh(self) -> None:
        if not self._auto_reload:
            return
        with self._lock:
            signature = self._scan_signature()
            if signature != self._signature:
                self._load(signature)

    def _folders(self) -> list[Path]:
        if not self._root.is_dir():
            return []
        return sorted(p for p in self._root.iterdir() if (p / META_FILE).is_file())

    def _scan_signature(self) -> _Signature:
        entries = []
        for folder in self._folders():
            st = (folder / META_FILE).stat()
            entries.append((folder.name, st.st_mtime_ns, st.st_size))
        return tuple(entries)

    def _load(self, signature: _Signature) -> None:
        exercises: dict[str, Exercise] = {}
        errors: list[ContentError] = []
        for folder in self._folders():
            try:
                exercises[folder.name] = _load_one(folder)
            except (ValueError, OSError) as exc:
                errors.append(ContentError(folder=folder.name, message=str(exc)))

        # Cross-references need the full set.
        for ex_id, ex in list(exercises.items()):
            missing = [r for r in ex.meta.requires if r not in exercises]
            if missing:
                del exercises[ex_id]
                names = ", ".join(f"'{m}'" for m in missing)
                errors.append(ContentError(ex_id, f"requires: soal {names} tidak ada"))

        for error in errors:
            log.warning("soal %s dilewati: %s", error.folder, error.message)
        self._exercises = exercises
        self._errors = errors
        self._signature = signature
