"""Turn user-supplied relative paths into filesystem paths that stay inside a base folder."""

from pathlib import Path, PurePosixPath, PureWindowsPath


class UnsafePathError(ValueError):
    pass


def safe_join(base: Path, user_path: str) -> Path:
    """Join base and user_path, refusing anything that could leave base.

    Rejects '..' segments, absolute paths, Windows drives and UNC paths, NUL bytes,
    and symlinks that resolve outside base. Backslashes are treated as separators.
    """
    if not user_path or "\x00" in user_path:
        raise UnsafePathError("path kosong atau mengandung karakter tidak valid")
    normalized = user_path.replace("\\", "/")
    rel = PurePosixPath(normalized)
    if rel.is_absolute() or PureWindowsPath(user_path).drive:
        raise UnsafePathError("path harus relatif")
    if ".." in rel.parts:
        raise UnsafePathError("path tidak boleh mengandung '..'")

    root = base.resolve()
    try:
        candidate = (root / rel).resolve()
    except (OSError, ValueError) as exc:
        raise UnsafePathError(str(exc)) from exc
    if not candidate.is_relative_to(root):  # e.g. a symlink pointing outside
        raise UnsafePathError("path keluar dari folder yang diizinkan")
    return candidate
