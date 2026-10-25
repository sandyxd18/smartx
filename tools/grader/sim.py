#!/usr/bin/env python3
"""Jalankan simulasi cocotb untuk proyek workspace SmartX.

Versi umum dari grade.py: banyak file sumber, banyak testbench, parameter, define,
dan pilihan simulator (icarus atau verilator). Spesifikasi dibaca dari file JSON
yang ditulis backend (lihat backend/app/jobs/kinds/sim.py):

    {"top": "fifo", "sources": ["src/fifo.v"], "tests": ["test/test_fifo.py"],
     "simulator": "icarus", "parameters": {"DEPTH": 8}, "defines": {"SIM": 1}}

Path di spec relatif terhadap --project. Hasil ditulis sebagai JSON ke --out.

Contoh:
    python tools/grader/sim.py --spec sim.json --project proj --workdir build --out result.json

Kode keluar: 0 = semua test lulus, 1 = ada yang gagal / error kompilasi,
2 = kesalahan pemakaian (spec tidak valid, file tidak ada).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from grade import parse_results  # noqa: E402

SIMULATORS = ("icarus", "verilator")
VERSION_COMMANDS = {"icarus": ["iverilog", "-V"], "verilator": ["verilator", "--version"]}


def simulator_version(simulator: str) -> str:
    """First line of the simulator's version output, recorded with the result."""
    try:
        proc = subprocess.run(
            VERSION_COMMANDS[simulator], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    lines = (proc.stdout or proc.stderr).strip().splitlines()
    return lines[0] if lines else ""


def build_args(simulator: str) -> list[str]:
    # Verilator writes VCD by default; FST is smaller and what WaveView loads.
    return ["--trace-fst"] if simulator == "verilator" else []


def find_waves(*folders: Path) -> Path | None:
    """Icarus writes <top>.fst into the build folder, Verilator dump.fst into the
    test folder; take the first waveform found."""
    for folder in folders:
        found = sorted(list(folder.glob("*.fst")) + list(folder.glob("*.vcd")))
        if found:
            return found[0]
    return None


def check_spec(spec: dict, project: Path) -> list[str]:
    problems = []
    for key in ("top", "sources", "tests", "simulator"):
        if key not in spec:
            problems.append(f"spec: '{key}' wajib ada")
    if problems:
        return problems
    if spec["simulator"] not in SIMULATORS:
        problems.append(f"simulator '{spec['simulator']}' tidak dikenal")
    if not spec["tests"]:
        problems.append("tidak ada testbench di 'tests'")
    for rel in [*spec["sources"], *spec["tests"]]:
        if not (project / rel).is_file():
            problems.append(f"file tidak ada: {rel}")
    return problems


def simulate(spec: dict, project: Path, workdir: Path) -> dict:
    from cocotb_tools.runner import get_runner  # import di sini agar --help tetap cepat

    simulator = spec["simulator"]
    sources = [project / s for s in spec["sources"]]
    tests = [project / t for t in spec["tests"]]
    workdir.mkdir(parents=True, exist_ok=True)
    build_dir = workdir / "sim_build"

    result: dict = {
        "top": spec["top"],
        "simulator": simulator,
        "simulator_version": simulator_version(simulator),
        "status": "error",
        "tests": [],
        "log": "",
        "wave_file": None,
    }

    runner = get_runner(simulator)
    build_log = workdir / "build.log"
    try:
        runner.build(
            sources=sources,
            hdl_toplevel=spec["top"],
            includes=list(dict.fromkeys(s.parent for s in sources)),
            defines=spec.get("defines", {}),
            parameters=spec.get("parameters", {}),
            build_args=build_args(simulator),
            build_dir=build_dir,
            waves=True,
            always=True,
            # Proyek tidak wajib menulis `timescale; samakan dengan soal latihan.
            timescale=("1ns", "1ps"),
            log_file=build_log,
        )
    except Exception as exc:  # error kompilasi
        result["status"] = "compile_error"
        result["log"] = build_log.read_text()[-20000:] if build_log.exists() else str(exc)
        return result

    # cocotb gives the test process PYTHONPATH = this process's sys.path, so a
    # testbench can import helpers that sit next to it (scoreboard.py, models.py).
    for folder in dict.fromkeys(t.parent for t in tests):
        sys.path.insert(0, str(folder))
    sim_log = workdir / "sim.log"
    results_xml = runner.test(
        hdl_toplevel=spec["top"],
        test_module=[t.stem for t in tests],
        build_dir=build_dir,
        test_dir=workdir,
        waves=True,
        log_file=sim_log,
    )

    result["tests"] = parse_results(Path(results_xml))
    result["log"] = sim_log.read_text()[-20000:] if sim_log.exists() else ""
    waves = find_waves(build_dir, workdir)
    result["wave_file"] = str(waves) if waves else None
    if not result["tests"]:
        result["status"] = "error"
    elif all(t["passed"] for t in result["tests"]):
        result["status"] = "pass"
    else:
        result["status"] = "fail"
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", required=True, type=Path, help="file JSON spesifikasi simulasi")
    ap.add_argument("--project", required=True, type=Path, help="folder proyek")
    ap.add_argument("--workdir", required=True, type=Path, help="folder kerja (build, log)")
    ap.add_argument("--out", required=True, type=Path, help="tulis JSON hasil ke file ini")
    args = ap.parse_args()

    spec = json.loads(args.spec.read_text())
    project = args.project.resolve()
    problems = check_spec(spec, project)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 2

    result = simulate(spec, project, args.workdir.resolve())
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"status: {result['status']}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
