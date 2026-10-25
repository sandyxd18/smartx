"""Map files a job wrote (paths as the container saw them) to download URLs."""

from pathlib import Path, PurePosixPath


def run_relative(container_path: object, run_dir: Path) -> str | None:
    """Map /work/... to a path relative to the run folder, if that file exists there."""
    if not isinstance(container_path, str):
        return None
    path = PurePosixPath(container_path)
    if not path.is_relative_to("/work") or ".." in path.parts:
        return None
    rel = path.relative_to("/work")
    return rel.as_posix() if (run_dir / rel).is_file() else None


def file_url(run_dir: Path, rel: str | None) -> str | None:
    return f"/api/runs/{run_dir.name}/files/{rel}" if rel else None
