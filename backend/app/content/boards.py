"""FPGA board profiles: content/boards/<id>.yaml plus a constraint template.

A profile says how to place, route and pack a design for one board with the tools
in the pinned toolchain image. Tool arguments are data because they differ per
family and change between tool versions; see docs/CONTENT-FORMAT.md.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

BoardId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]
FileName = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_][A-Za-z0-9_.-]*$")]
Word = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.-]+$")]

# Placeholders a profile may use in tool arguments, filled in by the fpga job.
PLACEHOLDERS = frozenset({"constraints", "pnr", "bitstream"})
_PLACEHOLDER = re.compile(r"\{([^{}]*)\}")

# How the constraint languages pin a port: IO_LOC "led[0]" 10; / set_io led[0] 11
_CST_PIN = re.compile(r'^\s*IO_LOC\s+"([^"]+)"\s+(\S+?)\s*;', re.MULTILINE)
_PCF_PIN = re.compile(r"^\s*set_io\s+(?:-\S+\s+)*(\S+)\s+(\S+)", re.MULTILINE)


class BoardError(ValueError):
    pass


class Tool(BaseModel):
    model_config = ConfigDict(extra="forbid")

    binary: Word
    args: list[str] = []


class Clock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    port: str = Field(min_length=1)  # port name used in the constraint template
    pin: str = Field(min_length=1)
    freq_mhz: float = Field(gt=0)


class Constraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["cst", "pcf"]
    template: FileName


class Board(BaseModel):
    """<id>.yaml"""

    model_config = ConfigDict(extra="forbid")

    id: BoardId
    name: str = Field(min_length=1)
    family: Literal["gowin", "ice40"]
    device: str = Field(min_length=1)
    synth: Literal["synth_gowin", "synth_ice40"]  # Yosys synthesis command
    nextpnr: Tool
    pnr_file: FileName  # what nextpnr writes for the packer ({pnr})
    pack: Tool
    bitstream_file: FileName  # what the packer writes ({bitstream})
    flash: Tool
    clock: Clock
    constraints: Constraints
    # Report rows: label -> nextpnr resource types summed into that row.
    resources: dict[str, list[Word]] = Field(min_length=1)


@dataclass(frozen=True)
class BoardProfile:
    board: Board
    constraints_template: str  # text of the template file


def _fill(args: list[str], values: dict[str, str]) -> list[str]:
    return [_PLACEHOLDER.sub(lambda m: values[m.group(1)], arg) for arg in args]


def nextpnr_command(
    board: Board, *, netlist: str, constraints: str, freq_mhz: float, report: str, log: str
) -> list[str]:
    """nextpnr call for a synthesized netlist. File names are relative to the run folder."""
    values = {"constraints": constraints, "pnr": board.pnr_file, "bitstream": board.bitstream_file}
    return [
        board.nextpnr.binary,
        "--json",
        netlist,
        *_fill(board.nextpnr.args, values),
        "--freq",
        f"{freq_mhz:g}",
        "--report",
        report,
        "-l",
        log,
    ]


def pack_command(board: Board) -> list[str]:
    values = {"constraints": "", "pnr": board.pnr_file, "bitstream": board.bitstream_file}
    return [board.pack.binary, *_fill(board.pack.args, values)]


def constraint_pins(fmt: str, text: str) -> dict[str, str]:
    """Port -> pin pairs pinned by a constraint file (comments are skipped by the regexes)."""
    pattern = _CST_PIN if fmt == "cst" else _PCF_PIN
    return {port: pin for port, pin in pattern.findall(text)}


def _check(board: Board, stem: str, template: str) -> None:
    if board.id != stem:
        raise BoardError(f"id '{board.id}' harus sama dengan nama file")
    for tool, needed in (
        (board.nextpnr, {"constraints", "pnr"}),
        (board.pack, {"pnr", "bitstream"}),
        (board.flash, set()),
    ):
        used = {name for arg in tool.args for name in _PLACEHOLDER.findall(arg)}
        if unknown := used - PLACEHOLDERS:
            raise BoardError(f"{tool.binary}: placeholder tidak dikenal {sorted(unknown)}")
        if missing := needed - used:
            raise BoardError(f"{tool.binary}: argumen harus memakai {sorted(missing)}")
    pins = constraint_pins(board.constraints.format, template)
    if pins.get(board.clock.port) != board.clock.pin:
        raise BoardError(
            f"template constraint harus memasang port clock '{board.clock.port}' "
            f"ke pin {board.clock.pin}"
        )


def _parse(path: Path) -> BoardProfile:
    try:
        board = Board.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
        template_path = path.parent / board.constraints.template
        if not template_path.is_file():
            raise BoardError(f"template constraint '{board.constraints.template}' tidak ada")
        template = template_path.read_text(encoding="utf-8")
        _check(board, path.stem, template)
    except (ValidationError, yaml.YAMLError, BoardError) as exc:
        raise BoardError(f"{path.name}: {exc}") from exc
    return BoardProfile(board=board, constraints_template=template)


def load_boards(boards_dir: Path) -> list[BoardProfile]:
    """All board profiles, ordered by id. A few small files, read on demand."""
    if not boards_dir.is_dir():
        return []
    return sorted((_parse(p) for p in boards_dir.glob("*.yaml")), key=lambda x: x.board.id)
