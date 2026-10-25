"""Copy a project's files into a run folder, so a run sees exactly what was clicked."""

from pathlib import Path

from app.paths import safe_join


def write_snapshot(dest: Path, files: dict[str, str]) -> None:
    """Write files (project path -> text) under dest. Paths were validated when saved;
    safe_join checks again, since this is where they touch the disk."""
    dest.mkdir(parents=True, exist_ok=True)
    for path, content in files.items():
        target = safe_join(dest, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
