"""Short lessons shown next to the workspace: content/lessons/NN-slug.md.

Each file starts with YAML front matter between '---' lines (title, step, order),
followed by the Markdown body. See docs/CONTENT-FORMAT.md.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class LessonError(ValueError):
    pass


class LessonMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    step: int = Field(ge=1, le=6)  # learning step (SPEC): 2 = simulation and verification
    order: int = 100


@dataclass(frozen=True)
class Lesson:
    id: str  # file name without .md
    title: str
    step: int
    order: int
    body: str  # Markdown


def _parse(path: Path) -> Lesson:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise LessonError(f"{path.name}: harus diawali front matter '---'")
    head, sep, body = text[4:].partition("\n---\n")
    if not sep:
        raise LessonError(f"{path.name}: front matter tidak ditutup dengan '---'")
    try:
        meta = LessonMeta.model_validate(yaml.safe_load(head) or {})
    except (ValidationError, yaml.YAMLError) as exc:
        raise LessonError(f"{path.name}: {exc}") from exc
    body = body.lstrip("\n")
    if not body.strip():
        raise LessonError(f"{path.name}: isi materi kosong")
    return Lesson(id=path.stem, title=meta.title, step=meta.step, order=meta.order, body=body)


def load_lessons(lessons_dir: Path) -> list[Lesson]:
    """All lessons, ordered by (step, order, id). Small files, read on demand."""
    if not lessons_dir.is_dir():
        return []
    lessons = [_parse(path) for path in lessons_dir.glob("*.md")]
    return sorted(lessons, key=lambda x: (x.step, x.order, x.id))
