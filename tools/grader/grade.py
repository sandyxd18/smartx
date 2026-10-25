#!/usr/bin/env python3
"""Grader untuk soal latihan ChipLab.

Menjalankan testbench cocotb sebuah soal terhadap file Verilog kiriman
pengguna, lalu menulis hasilnya sebagai JSON yang dibaca backend.

Contoh:
    python tools/grader/grade.py \
        --exercise content/exercises/counter-4bit \
        --source my_counter.v \
        --workdir /tmp/run-001 \
        --out /tmp/run-001/result.json

    # Uji soal dengan solusi resminya (dipakai di CI / make check-content):
    python tools/grader/grade.py --exercise content/exercises/counter-4bit --use-solution

Kode keluar: 0 = semua test lulus, 1 = ada yang gagal / error kompilasi,
2 = kesalahan pemakaian (soal tidak valid, file tidak ada).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml


def load_exercise(ex_dir: Path) -> dict:
    meta_path = ex_dir / "exercise.yaml"
    if not meta_path.is_file():
        raise SystemExit(f"exercise.yaml tidak ditemukan di {ex_dir}")
    meta = yaml.safe_load(meta_path.read_text())
    for key in ("id", "toplevel", "files"):
        if key not in meta:
            raise SystemExit(f"{meta_path}: field '{key}' wajib ada")
    return meta


def parse_results(xml_path: Path) -> list[dict]:
    tests = []
    if not xml_path.is_file():
        return tests
    root = ET.parse(xml_path).getroot()
    for case in root.iter("testcase"):
        failure = case.find("failure")
        error = case.find("error")
        problem = failure if failure is not None else error
        tests.append(
            {
                "name": case.get("name"),
                "passed": problem is None,
                "message": (problem.get("message") or problem.text or "").strip()
                if problem is not None
                else "",
                "sim_time_ns": float(case.get("sim_time_ns", 0) or 0),
            }
        )
    return tests


def grade(ex_dir: Path, source: Path, workdir: Path, simulator: str) -> dict:
    from cocotb_tools.runner import get_runner  # import di sini agar --help tetap cepat

    meta = load_exercise(ex_dir)
    test_file = ex_dir / meta["files"]["test"]
    test_module = test_file.stem

    workdir.mkdir(parents=True, exist_ok=True)
    # Salin testbench ke workdir agar soal asli tidak tersentuh.
    shutil.copy(test_file, workdir / test_file.name)
    src_copy = workdir / "dut.v"
    shutil.copy(source, src_copy)

    build_dir = workdir / "sim_build"
    runner = get_runner(simulator)
    result: dict = {
        "exercise": meta["id"],
        "simulator": simulator,
        "status": "error",
        "tests": [],
        "log": "",
        "wave_file": None,
    }

    log_path = workdir / "build.log"
    try:
        runner.build(
            sources=[src_copy],
            hdl_toplevel=meta["toplevel"],
            build_dir=build_dir,
            waves=True,
            always=True,
            # Soal tidak mewajibkan `timescale; tanpa ini presisi default 1 s
            # dan Clock 10 ns ditolak cocotb.
            timescale=("1ns", "1ps"),
            log_file=log_path,
        )
    except Exception as exc:  # error kompilasi Verilog
        result["status"] = "compile_error"
        result["log"] = log_path.read_text() if log_path.exists() else str(exc)
        return result

    results_xml = runner.test(
        hdl_toplevel=meta["toplevel"],
        test_module=test_module,
        test_dir=workdir,
        build_dir=build_dir,
        waves=True,
        log_file=workdir / "sim.log",
    )

    result["tests"] = parse_results(Path(results_xml))
    sim_log = workdir / "sim.log"
    result["log"] = sim_log.read_text()[-20000:] if sim_log.exists() else ""

    waves = sorted(list(build_dir.glob("*.fst")) + list(build_dir.glob("*.vcd")))
    result["wave_file"] = str(waves[0]) if waves else None

    if not result["tests"]:
        result["status"] = "error"
    elif all(t["passed"] for t in result["tests"]):
        result["status"] = "pass"
    else:
        result["status"] = "fail"
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exercise", required=True, type=Path, help="folder soal")
    ap.add_argument("--source", type=Path, help="file Verilog kiriman pengguna")
    ap.add_argument("--use-solution", action="store_true", help="pakai solution.v soal")
    ap.add_argument("--use-starter", action="store_true", help="pakai starter.v soal (harus gagal)")
    ap.add_argument("--workdir", type=Path, help="folder kerja (default: folder sementara)")
    ap.add_argument("--out", type=Path, help="tulis JSON hasil ke file ini")
    ap.add_argument("--simulator", default="icarus", choices=["icarus", "verilator"])
    args = ap.parse_args()

    ex_dir = args.exercise.resolve()
    meta = load_exercise(ex_dir)
    if args.use_solution:
        source = ex_dir / meta["files"]["solution"]
    elif args.use_starter:
        source = ex_dir / meta["files"]["starter"]
    elif args.source:
        source = args.source.resolve()
    else:
        print("Pilih salah satu: --source, --use-solution, atau --use-starter", file=sys.stderr)
        return 2
    if not source.is_file():
        print(f"File sumber tidak ada: {source}", file=sys.stderr)
        return 2

    workdir = (args.workdir or Path(tempfile.mkdtemp(prefix=f"grade-{meta['id']}-"))).resolve()
    result = grade(ex_dir, source, workdir, args.simulator)

    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        args.out.write_text(text)
    else:
        # Ringkasan untuk terminal; log lengkap ada di JSON.
        summary = {k: v for k, v in result.items() if k != "log"}
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
