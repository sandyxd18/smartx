from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from app.config import REPO_ROOT
from app.content.boards import (
    BoardError,
    constraint_pins,
    load_boards,
    nextpnr_command,
    pack_command,
)

BOARD = {
    "id": "papan-uji",
    "name": "Papan uji",
    "family": "gowin",
    "device": "GW1NR-LV9QN88PC6/I5",
    "synth": "synth_gowin",
    "nextpnr": {
        "binary": "nextpnr-himbaechel",
        "args": ["--device", "DEV", "--vopt", "cst={constraints}", "--write", "{pnr}"],
    },
    "pnr_file": "pnr.json",
    "pack": {"binary": "gowin_pack", "args": ["-o", "{bitstream}", "{pnr}"]},
    "bitstream_file": "bitstream.fs",
    "flash": {"binary": "openFPGALoader", "args": ["-b", "papan"]},
    "clock": {"port": "clk", "pin": "52", "freq_mhz": 27},
    "constraints": {"format": "cst", "template": "papan-uji.cst"},
    "resources": {"LUT": ["LUT4"], "FF": ["DFF"]},
}
TEMPLATE = '// clock\nIO_LOC "clk" 52;\n// IO_LOC "led" 9;\nIO_LOC "led[0]" 10;\n'


def write_board(folder: Path, board: dict[str, object], template: str = TEMPLATE) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "papan-uji.yaml").write_text(yaml.safe_dump(board), encoding="utf-8")
    (folder / "papan-uji.cst").write_text(template, encoding="utf-8")


def test_loads_profile_and_template(tmp_path: Path) -> None:
    write_board(tmp_path, BOARD)

    [profile] = load_boards(tmp_path)

    assert profile.board.id == "papan-uji"
    assert profile.board.clock.freq_mhz == 27
    assert profile.constraints_template == TEMPLATE


def test_commands_fill_placeholders(tmp_path: Path) -> None:
    write_board(tmp_path, BOARD)
    board = load_boards(tmp_path)[0].board

    assert nextpnr_command(
        board,
        netlist="netlist.json",
        constraints="project/board.cst",
        freq_mhz=27.0,
        report="report.json",
        log="nextpnr.log",
    ) == [
        "nextpnr-himbaechel",
        "--json",
        "netlist.json",
        "--device",
        "DEV",
        "--vopt",
        "cst=project/board.cst",
        "--write",
        "pnr.json",
        "--freq",
        "27",
        "--report",
        "report.json",
        "-l",
        "nextpnr.log",
    ]
    assert pack_command(board) == ["gowin_pack", "-o", "bitstream.fs", "pnr.json"]


def test_constraint_pins_skip_comments() -> None:
    assert constraint_pins("cst", TEMPLATE) == {"clk": "52", "led[0]": "10"}
    pcf = "# clock\nset_io clk 35\nset_io -nowarn led[0] 11\n# set_io x 1\n"
    assert constraint_pins("pcf", pcf) == {"clk": "35", "led[0]": "11"}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"id": "lain"}, "nama file"),
        ({"warna": "biru"}, "warna"),  # unknown key
        ({"family": "xilinx"}, "family"),
        ({"constraints": {"format": "cst", "template": "tidak-ada.cst"}}, "tidak ada"),
        ({"constraints": {"format": "cst", "template": "../luar.cst"}}, "template"),
        ({"nextpnr": {"binary": "nextpnr", "args": ["--write", "{pnr}"]}}, "constraints"),
        ({"pack": {"binary": "gowin_pack", "args": ["{pnr}", "{output}"]}}, "output"),
        ({"clock": {"port": "clk", "pin": "53", "freq_mhz": 27}}, "pin 53"),
        ({"clock": {"port": "osc", "pin": "52", "freq_mhz": 27}}, "osc"),
        ({"resources": {}}, "resources"),
    ],
)
def test_invalid_profiles_are_reported(
    tmp_path: Path, change: dict[str, object], message: str
) -> None:
    write_board(tmp_path, {**BOARD, **change})
    with pytest.raises(BoardError, match=message) as exc:
        load_boards(tmp_path)
    assert str(exc.value).startswith("papan-uji.yaml: ")


def test_content_boards_are_valid() -> None:
    profiles = load_boards(REPO_ROOT / "content" / "boards")

    assert [p.board.id for p in profiles] == ["tang-nano-9k"]
    tang = profiles[0]
    pins = constraint_pins("cst", tang.constraints_template)
    assert pins["clk"] == "52"
    assert [pins[f"led[{i}]"] for i in range(6)] == ["10", "11", "13", "14", "15", "16"]


def test_api_lists_boards_with_template(client: TestClient) -> None:
    [tang] = client.get("/api/boards").json()

    assert tang["id"] == "tang-nano-9k"
    assert tang["clock_port"] == "clk" and tang["clock_mhz"] == 27
    assert tang["constraints_format"] == "cst"
    assert 'IO_LOC "clk" 52;' in tang["constraints_template"]
    # Build tool arguments are internal to the fpga job; flashing runs on the host.
    assert "nextpnr" not in tang
    assert tang["flash_command"] == ["openFPGALoader", "-b", "tangnano9k"]


def test_fpga_templates_match_their_board() -> None:
    """Example projects carry a copy of the board's constraint template; keep it in step,
    and keep their smartx.yaml valid for Build."""
    from app.projects.run_params import run_params
    from app.projects.templates import load_templates

    profiles = {p.board.id: p for p in load_boards(REPO_ROOT / "content" / "boards")}
    boards = {board_id: p.board for board_id, p in profiles.items()}
    fpga_templates = [
        t for t in load_templates(REPO_ROOT / "content" / "templates") if t.id.startswith("fpga-")
    ]

    assert [t.id for t in fpga_templates] == ["fpga-blinky", "fpga-counter-led", "fpga-button"]
    for template in fpga_templates:
        files = template.files()
        params = run_params("fpga", files, boards)
        board = profiles[params["board"]]
        assert files[params["constraints"]] == board.constraints_template, template.id
        # The simulation and the board use different values for the same parameter.
        sim = run_params("sim", files, boards)
        assert sim["parameters"] != params["parameters"], template.id
