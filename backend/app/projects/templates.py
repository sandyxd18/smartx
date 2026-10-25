"""Starting points for a new project: content/templates/<id>/ and copies of an exercise.

A template folder holds template.yaml (title, description, order) and a files/ folder
whose contents become the project. See docs/CONTENT-FORMAT.md.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.content import Exercise
from app.projects.paths import normalize_project_path


class TemplateMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    description: str = ""
    order: int = 100


@dataclass(frozen=True)
class Template:
    id: str
    meta: TemplateMeta
    dir: Path

    def files(self) -> dict[str, str]:
        """Project path -> text, read from files/ (validated like user paths)."""
        root = self.dir / "files"
        found: dict[str, str] = {}
        for path in sorted(root.rglob("*")):
            if path.is_file():
                rel = normalize_project_path(path.relative_to(root).as_posix())
                found[rel] = path.read_text(encoding="utf-8")
        return found


def load_templates(templates_dir: Path) -> list[Template]:
    """All templates, ordered by (order, id). Small and rarely used, so read on demand."""
    templates = []
    if templates_dir.is_dir():
        for folder in templates_dir.iterdir():
            meta_path = folder / "template.yaml"
            if meta_path.is_file():
                meta = TemplateMeta.model_validate(
                    yaml.safe_load(meta_path.read_text(encoding="utf-8"))
                )
                templates.append(Template(id=folder.name, meta=meta, dir=folder))
    return sorted(templates, key=lambda t: (t.meta.order, t.id))


def exercise_files(exercise: Exercise, code: str) -> dict[str, str]:
    """A project to keep working on an exercise: the user's code, its testbench, the
    statement and a config. Never the solution."""
    top = exercise.meta.toplevel
    ext = "sv" if exercise.meta.language == "systemverilog" else "v"
    test = exercise.test_path
    config = (
        "# Konfigurasi proyek SmartX (lihat docs/CONTENT-FORMAT.md, bagian Proyek workspace).\n"
        f"top: {top}\n"
        "sources:\n"
        f"  - src/**/*.{ext}\n"
        "tests:\n"
        f"  - test/{test.name}\n"
        "simulator: icarus\n"
    )
    return {
        "README.md": exercise.read_statement(),
        "smartx.yaml": config,
        f"src/{top}.{ext}": code,
        f"test/{test.name}": test.read_text(encoding="utf-8"),
    }
