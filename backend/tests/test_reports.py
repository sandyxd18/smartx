"""Report parsers against real tool output (pinned Yosys 0.70+219, nextpnr 0.11.1-79).

The Yosys logs in fixtures/reports/ are trimmed copies of real logs of the designs
in fixtures/reports/src/; the nextpnr reports belong to the fpga run fixtures.
"""

import json
import re
from pathlib import Path

import pytest

from app.reports.nextpnr import clock_name, clocks, critical_paths, input_ports, utilization
from app.reports.yosys import parse_yosys_log, unused_inputs

REPORTS = Path(__file__).parent / "fixtures" / "reports"
RUNS = Path(__file__).parent / "fixtures" / "runs"
ROOT = "/work/project"
TANG = {"LUT": ["LUT4"], "FF": ["DFF"], "BRAM": ["BSRAM"], "IO": ["IOB"]}


def yosys(name: str) -> list[tuple[str, str | None, str | None, int | None]]:
    sources = {f"src/{name}.v": (REPORTS / "src" / f"{name}.v").read_text(encoding="utf-8")}
    log = (REPORTS / f"{name}.log").read_text(encoding="utf-8")
    return [(w.kind, w.signal, w.file, w.line) for w in parse_yosys_log(log, sources, ROOT)]


def report(run: str) -> dict:
    return json.loads((RUNS / run / "build" / "report.json").read_text(encoding="utf-8"))


def raw_log(run: str) -> str:
    return (RUNS / run / "build" / "nextpnr.log").read_text(encoding="utf-8")


class TestYosysWarnings:
    def test_latch_points_at_the_always_block(self) -> None:
        assert yosys("latch") == [("latch", "q", "src/latch.v", 2)]

    def test_multiple_drivers_name_the_users_signals(self) -> None:
        # Yosys merges x with both inputs, so it also names b; nets it created while
        # mapping (a_IBUF_I_O_DFF_D_Q in multi2) are left out.
        assert yosys("multi") == [
            ("multi_driven", "b", "src/multi.v", 1),
            ("multi_driven", "x", "src/multi.v", 2),
        ]
        assert yosys("multi2") == [("multi_driven", "y", "src/multi2.v", 1)]

    def test_undriven_and_implicit_signals(self) -> None:
        assert yosys("unused") == [
            ("implicit", "implicit_w", "src/unused.v", 6),
            ("undriven", "implicit_w", None, None),  # never declared
            ("undriven", "nodrv", "src/unused.v", 2),
        ]

    def test_memory_built_from_flip_flops(self) -> None:
        assert yosys("mem") == [("memory_ff", "mem", "src/mem.v", 2)]

    def test_messages_explain_the_fix(self) -> None:
        log = (REPORTS / "latch.log").read_text(encoding="utf-8")
        [warning] = parse_yosys_log(log, {}, ROOT)
        assert warning.message.startswith("Latch terbentuk untuk `q`")
        assert "`else`" in warning.message and "`default`" in warning.message

    def test_other_warnings_about_project_files_are_kept(self) -> None:
        log = (
            "/work/project/src/a.v:3: Warning: Something new.\n"
            "/opt/oss-cad-suite/share/yosys/x.v:1: Warning: about the library\n"
            "Lexer warning: The SystemVerilog keyword `bit' (at /opt/x.v:35) ...\n"
            "ABC: Warning: The network is combinational.\n"
            "Warnings: 1 unique messages, 1 total\n"
        )
        [w] = parse_yosys_log(log, {}, ROOT)
        assert (w.kind, w.file, w.line, w.message) == ("other", "src/a.v", 3, "Something new.")

    def test_unused_inputs_from_the_netlist(self) -> None:
        netlist = json.loads((REPORTS / "unused.netlist.json").read_text(encoding="utf-8"))
        # y = a & nodrv folds to 0, so a drives nothing; unused_in is skipped by name.
        assert unused_inputs(netlist, "top") == ["clk", "a"]

    def test_unused_input_bits(self) -> None:
        netlist = {
            "modules": {
                "top": {
                    "ports": {
                        "sw": {"direction": "input", "bits": [2, 3, 4]},
                        "led": {"direction": "output", "bits": [5]},
                    },
                    "cells": {
                        "and": {
                            "type": "LUT2",
                            "port_directions": {"I0": "input", "I1": "input", "F": "output"},
                            "connections": {"I0": [2], "I1": [4], "F": [5]},
                        }
                    },
                }
            }
        }
        assert unused_inputs(netlist, "top") == ["sw[1]"]
        assert unused_inputs(netlist, "other") == []


class TestNextpnrReport:
    def test_utilization_rows_from_the_board_profile(self) -> None:
        rows = utilization(report("fpga-ok"), TANG)

        assert [(r.label, r.used, r.available, r.percent) for r in rows] == [
            ("LUT", 43, 8640, 0.5),
            ("FF", 31, 6480, 0.5),
            ("BRAM", 0, 26, 0.0),
            ("IO", 8, 276, 2.9),
        ]

    def test_utilization_sums_types_and_tolerates_missing_ones(self) -> None:
        raw = {
            "utilization": {"A": {"used": 3, "available": 10}, "B": {"used": 1, "available": 10}}
        }
        [row] = utilization(raw, {"X": ["A", "B", "C"]})
        assert (row.used, row.available, row.percent) == (4, 20, 20.0)
        assert utilization({}, {"X": ["A"]})[0].percent == 0.0

    @pytest.mark.parametrize(("run", "met"), [("fpga-ok", True), ("fpga-timing-fail", False)])
    def test_fmax_matches_the_raw_log(self, run: str, met: bool) -> None:
        """Phase 3 criterion: the report shows the Fmax nextpnr itself printed last."""
        [clock] = clocks(report(run))
        *_, last = re.findall(
            r"Max frequency for clock '(\S+)': ([\d.]+) MHz \((PASS|FAIL) at ([\d.]+) MHz\)",
            raw_log(run),
        )
        net, achieved, verdict, target = last

        assert clock.net == net and clock.name == "clk"
        assert f"{clock.achieved_mhz:.2f}" == achieved
        assert f"{clock.target_mhz:.2f}" == target
        assert clock.met is met and verdict == ("PASS" if met else "FAIL")

    @pytest.mark.parametrize("run", ["fpga-ok", "fpga-timing-fail"])
    def test_critical_path_matches_the_raw_log(self, run: str) -> None:
        [path] = critical_paths(report(run), ROOT)
        log = raw_log(run)
        logic, routing = re.findall(r"([\d.]+) ns logic, ([\d.]+) ns routing", log)[-1]

        assert (path.from_clock, path.to_clock) == ("posedge clk", "posedge clk")
        assert f"{path.logic_ns:.2f}" == logic and f"{path.routing_ns:.2f}" == routing
        assert path.steps[0].type == "clk-to-q" and path.steps[-1].type == "setup"
        assert path.steps[-1].total_ns == path.delay_ns
        # Fmax is 1 / delay of the critical path.
        [clock] = clocks(report(run))
        assert abs(1000 / path.delay_ns - clock.achieved_mhz) < 0.5
        # Nets from the user's code point back at it; library nets do not.
        placed = [(s.name, s.file, s.line) for s in path.steps if s.file]
        assert placed and all(f == "src/blinky.v" for _, f, _ in placed)

    @pytest.mark.parametrize(
        ("net", "name"),
        [
            ("clk_IBUF_I_O", "clk"),
            ("sys_clk_IBUF_I_O", "sys_clk"),
            ("clk$SB_IO_IN_$glb_clk", "clk"),
            ("pll_out", "pll_out"),
        ],
    )
    def test_clock_names(self, net: str, name: str) -> None:
        assert clock_name(net) == name


def test_hierarchical_clock_net_is_named_after_the_top_port() -> None:
    """Shape measured on button_counter: nextpnr reports 'u_db.clk', the IBUF output."""
    netlist = {
        "modules": {
            "button_counter": {
                "ports": {
                    "clk": {"direction": "input", "bits": [2]},
                    "btn": {"direction": "input", "bits": [3]},
                    "led": {"direction": "output", "bits": [4, 5]},
                },
                "cells": {
                    "u_db.clk_IBUF_O": {"type": "IBUF", "connections": {"I": [2], "O": [12]}},
                    "btn_IBUF_I": {"type": "IBUF", "connections": {"I": [3], "O": [10]}},
                },
                "netnames": {
                    "clk": {"bits": [2]},
                    "u_db.clk": {"bits": [12]},
                    "u_sync.clk": {"bits": [12]},
                    "u_db.count": {"bits": [20, 21]},
                },
            }
        }
    }
    ports = input_ports(netlist, "button_counter")
    assert ports == {"clk": "clk", "u_db.clk": "clk", "u_sync.clk": "clk"}

    report = {"fmax": {"u_db.clk": {"achieved": 169.38, "constraint": 27}}}
    [clock] = clocks(report, ports)
    assert (clock.net, clock.name) == ("u_db.clk", "clk")
    # Without the netlist the net name is kept as it is.
    assert clocks(report)[0].name == "u_db.clk"
    paths = {"critical_paths": [{"from": "posedge u_db.clk", "to": "posedge u_db.clk"}]}
    [path] = critical_paths(paths, ROOT, ports)
    assert (path.from_clock, path.to_clock) == ("posedge clk", "posedge clk")
