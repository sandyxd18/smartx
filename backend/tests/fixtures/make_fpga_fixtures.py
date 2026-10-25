"""Rebuild the fpga run fixtures (tests/fixtures/runs/fpga-*) with the real toolchain.

Runs the fpga job's container for each case with the docker CLI and keeps a small
copy of the run folder: big outputs are trimmed (Yosys log, netlist) or replaced
(bitstream). Rerun after pinning a new OSS CAD Suite, then fix what the tests find.

    cd backend && uv run python tests/fixtures/make_fpga_fixtures.py
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.config import REPO_ROOT, Settings
from app.content import ExerciseCatalog
from app.jobs.context import JobContext
from app.jobs.kinds import fpga
from app.projects.snapshot import write_snapshot

FIXTURES = Path(__file__).parent
BLINKY = FIXTURES / "projects" / "blinky"
OUT = FIXTURES / "runs"
PARAMS = {
    "top": "blinky",
    "sources": ["src/blinky.v"],
    "board": "tang-nano-9k",
    "constraints": "constraints/tang-nano-9k.cst",
    "freq_mhz": 27,
}


def cases() -> dict[str, tuple[dict[str, str], float]]:
    files = {
        p.relative_to(BLINKY).as_posix(): p.read_text(encoding="utf-8")
        for p in BLINKY.rglob("*")
        if p.is_file()
    }
    cst = files["constraints/tang-nano-9k.cst"]
    latch = (FIXTURES / "designs" / "blinky_latch.v").read_text(encoding="utf-8")
    return {
        "fpga-ok": (files, 27),
        "fpga-synth-error": (
            {**files, "src/blinky.v": files["src/blinky.v"].replace("count = 0;", "count")},
            27,
        ),
        "fpga-warnings": ({**files, "src/blinky.v": latch}, 27),
        "fpga-timing-fail": (files, 300),
        "fpga-pnr-error": (
            {**files, "constraints/tang-nano-9k.cst": cst.replace('IO_LOC "led[5]" 16;', "")},
            27,
        ),
    }


def run(run_dir: Path, files: dict[str, str], freq: float, settings: Settings) -> int:
    ctx = JobContext(settings=settings, catalog=ExerciseCatalog(settings.content_dir / "exercises"))
    write_snapshot(run_dir / "project", files)
    spec = fpga.prepare(run_dir, {**PARAMS, "freq_mhz": freq}, ctx)
    env = [arg for k, v in spec.env.items() for arg in ("-e", f"{k}={v}")]
    proc = subprocess.run(
        [
            "docker", "run", "--rm", "--network", "none", *env,
            "-v", f"{run_dir}:/work", "-v", f"{REPO_ROOT / 'tools'}:/tools:ro",
            "-w", "/work", settings.toolchain_image, *spec.command,
        ],
        capture_output=True, text=True, encoding="utf-8",
    )  # fmt: skip
    (run_dir / "run.log").write_text(proc.stdout + proc.stderr, encoding="utf-8", newline="\n")
    return proc.returncode


def keep(run_dir: Path, dest: Path) -> None:
    shutil.rmtree(dest, ignore_errors=True)
    (dest / "build").mkdir(parents=True)
    shutil.copytree(run_dir / "project", dest / "project")  # collect() reads the sources
    for rel in ["fpga.json", "result.json", "run.log"]:
        shutil.copy(run_dir / rel, dest / rel)
    build = run_dir / "build"
    for rel in ["synth.ys", "stat.txt", "stat.json", "report.json", "nextpnr.log"]:
        if (build / rel).is_file():
            shutil.copy(build / rel, dest / "build" / rel)
    if (build / "yosys.log").is_file():  # 55 kB for blinky: head, what parsers read, tail
        lines = (build / "yosys.log").read_text(encoding="utf-8").splitlines(keepends=True)
        wanted = ("arning", "mapping for memory", "ERROR")
        middle = [x for x in lines[20:-40] if any(w in x for w in wanted)]
        kept = lines if len(lines) < 80 else [*lines[:20], "[...]\n", *middle, *lines[-40:]]
        (dest / "build" / "yosys.log").write_text("".join(kept), encoding="utf-8", newline="\n")
    if (build / "netlist.json").is_file():  # 1 MB: keep what unused_inputs()/input_ports() read
        top = json.loads((build / "netlist.json").read_text(encoding="utf-8"))["modules"]["blinky"]
        cells = {
            name: {k: cell[k] for k in ("type", "port_directions", "connections")}
            for name, cell in top["cells"].items()
        }
        netnames = {name: {"bits": net["bits"]} for name, net in top["netnames"].items()}
        module = {"ports": top["ports"], "cells": cells, "netnames": netnames}
        small = {"modules": {"blinky": module}}
        (dest / "build" / "netlist.json").write_text(json.dumps(small), encoding="utf-8")
    if (build / "bitstream.fs").is_file():  # 2 MB; collect() only needs it to exist
        (dest / "build" / "bitstream.fs").write_text("stand-in for a 2 MB bitstream\n")


def main() -> None:
    settings = Settings(content_dir=REPO_ROOT / "content")
    with tempfile.TemporaryDirectory() as tmp:
        for name, (files, freq) in cases().items():
            run_dir = Path(tmp) / name
            print(name, "exit", run(run_dir, files, freq, settings))
            keep(run_dir, OUT / name)


if __name__ == "__main__":
    main()
