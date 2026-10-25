#!/usr/bin/env python3
"""Bangun bitstream FPGA untuk proyek workspace SmartX, tahap demi tahap.

Backend (backend/app/jobs/kinds/fpga.py) sudah menyusun perintah setiap tahap dari
profil board; skrip ini hanya menjalankannya berurutan di --workdir, mencatat waktu
dan kode keluar tiap tahap, lalu berhenti di tahap pertama yang gagal:

    {"stages": [{"id": "synth", "title": "Synthesize", "command": ["yosys", ...]},
                {"id": "pnr", ...}, {"id": "pack", ...}],
     "versions": {"yosys": ["yosys", "-V"], ...}}

Keluaran tiap tahap diteruskan ke stdout (log run), diawali baris "==> <judul>".
Hasil ditulis sebagai JSON ke --out.

Kode keluar: 0 = semua tahap berhasil, 1 = ada tahap yang gagal,
2 = kesalahan pemakaian (spec tidak valid).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def tool_version(command: list[str]) -> str:
    """First line of a version command's output, recorded with the result."""
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    lines = (proc.stdout or proc.stderr).strip().splitlines()
    return lines[0] if lines else ""


def check_spec(spec: dict) -> list[str]:
    stages = spec.get("stages")
    if not isinstance(stages, list) or not stages:
        return ["spec: 'stages' wajib berisi minimal satu tahap"]
    problems = []
    for i, stage in enumerate(stages):
        for key in ("id", "title", "command"):
            if key not in stage:
                problems.append(f"spec: stages[{i}].{key} wajib ada")
    return problems


def run_stage(stage: dict, workdir: Path) -> dict:
    print(f"==> {stage['title']}", flush=True)
    start = time.monotonic()
    try:
        proc = subprocess.run(stage["command"], cwd=workdir, stderr=subprocess.STDOUT)
        exit_code = proc.returncode
    except OSError as exc:  # the tool is missing from the image
        print(f"tidak bisa menjalankan {stage['command'][0]}: {exc}", flush=True)
        exit_code = 127
    seconds = round(time.monotonic() - start, 2)
    status = "ok" if exit_code == 0 else "failed"
    print(f"<== {stage['title']}: {status} ({seconds} s)", flush=True)
    return {
        "id": stage["id"],
        "title": stage["title"],
        "status": status,
        "seconds": seconds,
        "exit_code": exit_code,
    }


def build(spec: dict, workdir: Path) -> dict:
    workdir.mkdir(parents=True, exist_ok=True)
    stages = []
    failed = False
    for stage in spec["stages"]:
        if failed:
            stages.append(
                {"id": stage["id"], "title": stage["title"], "status": "skipped",
                 "seconds": None, "exit_code": None}
            )
            continue
        stages.append(run_stage(stage, workdir))
        failed = stages[-1]["status"] == "failed"
    return {
        "status": "failed" if failed else "ok",
        "stages": stages,
        "versions": {name: tool_version(cmd) for name, cmd in spec.get("versions", {}).items()},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", required=True, type=Path, help="file JSON berisi tahap build")
    ap.add_argument("--workdir", required=True, type=Path, help="folder kerja semua tahap")
    ap.add_argument("--out", required=True, type=Path, help="tulis JSON hasil ke file ini")
    args = ap.parse_args()

    spec = json.loads(args.spec.read_text())
    problems = check_spec(spec)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 2

    result = build(spec, args.workdir.resolve())
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"status: {result['status']}")
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
