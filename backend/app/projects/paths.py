"""Validate file paths inside a project.

Project files live in the database, but every run writes them to a run folder on the
host, which may be Windows. A path is therefore accepted only if it is safe and portable
there too: relative, '/'-separated, no '.'/'..' segments, plain characters, no Windows
reserved device names. Uniqueness is checked case-insensitively in tree.py.
"""

import re

MAX_PATH_CHARS = 200
MAX_DEPTH = 8

# Starts with a letter, digit or '_' (no hidden files), ends with anything but '.'.
_SEGMENT = re.compile(r"^[A-Za-z0-9_](?:[A-Za-z0-9_.-]*[A-Za-z0-9_-])?$")
_RESERVED = {"con", "prn", "aux", "nul"} | {f"{p}{i}" for p in ("com", "lpt") for i in range(10)}


class InvalidProjectPath(ValueError):
    pass


def normalize_project_path(raw: str) -> str:
    """Return the canonical form of raw ('src/a.v'), or raise InvalidProjectPath."""
    path = raw.strip()
    if path.endswith("/"):
        path = path[:-1]
    if not path:
        raise InvalidProjectPath("Path tidak boleh kosong.")
    if len(path) > MAX_PATH_CHARS:
        raise InvalidProjectPath(f"Path terlalu panjang (maksimal {MAX_PATH_CHARS} karakter).")
    if "\\" in path:
        raise InvalidProjectPath("Gunakan '/' sebagai pemisah folder, bukan '\\'.")
    if path.startswith("/") or re.match(r"^[A-Za-z]:", path):
        raise InvalidProjectPath("Path harus relatif terhadap folder proyek.")
    segments = path.split("/")
    if len(segments) > MAX_DEPTH:
        raise InvalidProjectPath(f"Folder terlalu dalam (maksimal {MAX_DEPTH} tingkat).")
    for segment in segments:
        if segment in ("", ".", ".."):
            raise InvalidProjectPath("Path tidak boleh berisi '//', '.', atau '..'.")
        if not _SEGMENT.match(segment):
            raise InvalidProjectPath(
                f"Nama '{segment}' tidak valid. Pakai huruf, angka, '_', '-', dan '.'; "
                "jangan diawali '.' atau diakhiri '.'."
            )
        if segment.split(".")[0].lower() in _RESERVED:
            raise InvalidProjectPath(f"Nama '{segment}' dicadangkan oleh Windows.")
    return path


def ancestors(path: str) -> list[str]:
    """Folders that contain path, outermost first: 'a/b/c.v' -> ['a', 'a/b']."""
    parts = path.split("/")
    return ["/".join(parts[:i]) for i in range(1, len(parts))]
