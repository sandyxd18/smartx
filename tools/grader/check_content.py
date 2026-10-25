#!/usr/bin/env python3
"""Validasi semua soal di content/exercises.

Aturan untuk setiap soal:
  1. exercise.yaml valid dan semua file yang disebut ada.
  2. solution.v LULUS semua test.
  3. starter.v TIDAK lulus (kalau lulus, soalnya tidak menguji apa-apa).
  4. solution.v bersih dari peringatan `verilator --lint-only -Wall` (solusi resmi
     adalah contoh yang ditiru pengguna).

Contoh:
    python tools/grader/check_content.py              # semua soal
    python tools/grader/check_content.py counter-4bit # satu soal
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from grade import grade  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
EXERCISES = ROOT / "content" / "exercises"
REQUIRED = ("id", "title", "step", "level", "toplevel", "files")
REQUIRED_FILES = ("starter", "solution", "test", "statement")


def check_one(ex_dir: Path) -> list[str]:
    problems: list[str] = []
    meta = yaml.safe_load((ex_dir / "exercise.yaml").read_text())
    for key in REQUIRED:
        if key not in meta:
            problems.append(f"field '{key}' tidak ada")
    if meta.get("id") != ex_dir.name:
        problems.append(f"id '{meta.get('id')}' harus sama dengan nama folder '{ex_dir.name}'")
    for key in REQUIRED_FILES:
        name = meta.get("files", {}).get(key)
        if not name or not (ex_dir / name).is_file():
            problems.append(f"files.{key} ({name}) tidak ditemukan")
    if problems:
        return problems

    with tempfile.TemporaryDirectory() as tmp:
        sol = grade(ex_dir, ex_dir / meta["files"]["solution"], Path(tmp) / "sol", "icarus")
        if sol["status"] != "pass":
            failed = [t["name"] for t in sol["tests"] if not t["passed"]]
            problems.append(f"solution.v tidak lulus (status={sol['status']}, gagal={failed})")
        lint = [ln for ln in sol["lint_log"].splitlines() if ln.startswith("%")]
        if lint:
            problems.append("solution.v punya peringatan Verilator: " + " | ".join(lint))
        start = grade(ex_dir, ex_dir / meta["files"]["starter"], Path(tmp) / "start", "icarus")
        if start["status"] == "pass":
            problems.append("starter.v lulus semua test; testbench terlalu lemah")
    return problems


def main(argv: list[str]) -> int:
    targets = [EXERCISES / name for name in argv] if argv else sorted(
        p for p in EXERCISES.iterdir() if (p / "exercise.yaml").is_file()
    )
    failures = 0
    for ex_dir in targets:
        problems = check_one(ex_dir)
        if problems:
            failures += 1
            print(f"FAIL {ex_dir.name}")
            for p in problems:
                print(f"     - {p}")
        else:
            print(f"ok   {ex_dir.name}")
    print(f"\n{len(targets) - failures}/{len(targets)} soal valid")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
