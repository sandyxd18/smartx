"""Turn a project's smartx.yaml into the params of a lint, sim, or fpga run."""

from collections.abc import Mapping
from typing import Any, Literal

from app.content.boards import Board
from app.projects.config import CONFIG_PATH, analyze

RunKind = Literal["lint", "sim", "fpga"]


class RunConfigError(ValueError):
    """The project cannot run this kind of job yet; the message says why (Indonesian)."""


def run_params(kind: RunKind, files: dict[str, str], boards: Mapping[str, Board]) -> dict[str, Any]:
    """Params for a run of `kind` on a project with these files (path -> content)."""
    if CONFIG_PATH not in files:
        raise RunConfigError(f"{CONFIG_PATH} belum ada. Buat dulu lewat file baru atau form.")
    analysis = analyze(files[CONFIG_PATH], files, boards)
    config = analysis.config
    if config is None:
        first = analysis.problems[0]
        where = f" (baris {first.line})" if first.line else ""
        raise RunConfigError(f"{CONFIG_PATH} belum valid{where}: {first.message}")
    if not analysis.sources:
        raise RunConfigError(
            f"Pola 'sources' di {CONFIG_PATH} tidak cocok dengan file apa pun di proyek."
        )

    params: dict[str, Any] = {
        "top": config.top,
        "sources": analysis.sources,
        "defines": config.defines,
        "parameters": config.parameters,
    }
    if kind == "sim":
        if not config.tests:
            raise RunConfigError(
                f"Belum ada testbench di 'tests' pada {CONFIG_PATH}. Pilih minimal satu file test."
            )
        missing = [t for t in config.tests if t not in files]
        if missing:
            raise RunConfigError(f"File test tidak ada di proyek: {', '.join(missing)}.")
        params = {**params, "tests": config.tests, "simulator": config.simulator}
    if kind == "fpga":
        fpga = config.fpga
        if fpga is None:
            raise RunConfigError(
                f"Bagian 'fpga' belum ada di {CONFIG_PATH}. Pilih board dan file constraint dulu."
            )
        board = boards.get(fpga.board)
        if board is None:
            raise RunConfigError(f"Board '{fpga.board}' tidak dikenal.")
        if fpga.constraints not in files:
            raise RunConfigError(f"File constraint '{fpga.constraints}' tidak ada di proyek.")
        params = {
            **params,
            "board": board.id,
            "constraints": fpga.constraints,
            "freq_mhz": fpga.freq_mhz or board.clock.freq_mhz,
            # Build-only values win over the simulation's.
            "parameters": {**config.parameters, **fpga.parameters},
            "defines": {**config.defines, **fpga.defines},
        }
    return params
